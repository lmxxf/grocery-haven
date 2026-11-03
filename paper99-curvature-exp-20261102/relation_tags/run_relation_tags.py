#!/usr/bin/env python3
import sys,json,time,hashlib,gc,argparse
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent
sys.path[:0]=[str(PARENT),str(PARENT/'basepost')]
import run_curvature_experiments as core
from load_pair import load,memory,drop
from protocol import cases,save_protocol,ROLE_RE,QUESTION_LABELS
MODELS=['Qwen3.5-35B-A3B-Base','Qwen3-0.6B','Qwen3.5-35B-A3B']
class PlainTokenizer:
 def __init__(self,tok,prompt,pad):self.tok=tok;self.prompt=prompt;self.pad=pad
 @property
 def eos_token_id(self):return self.pad
 def __call__(self,*a,**k):return self.tok(*a,**k)
 def apply_chat_template(self,*a,**k):return self.prompt  # Does not invoke the real template.
 def __getattr__(self,key):return getattr(self.tok,key)

def parse_turn(tok,ids,condition):
 full=tok.decode(ids,skip_special_tokens=False,clean_up_tokenization_spaces=False)
 start=0;echo=False
 first=next((m for m in ROLE_RE.finditer(full) if not full[:m.start()].strip()),None)
 if first and first.group(1).casefold()==condition['right'].casefold():start=first.end();echo=True
 role_events=[dict(start=m.start(),end=m.end(),label=m.group(1),kind='role') for m in ROLE_RE.finditer(full) if m.start()>=start]
 candidates=[x for x in role_events if x['label'].casefold() in QUESTION_LABELS]
 # Model-emitted chat controls are output events, never part of any input.
 for special in ['<|im_start|>','<|im_end|>','<|endoftext|>']:
  i=full.find(special,start)
  if i>=0:candidates.append(dict(start=i,end=i+len(special),label=special,kind='special'))
 boundary=min(candidates,key=lambda x:x['start']) if candidates else None
 end=boundary['start'] if boundary else len(full)
 # Map original generated IDs via stable decoded character prefixes. This retains
 # partial UTF-8 token pieces without retokenizing the generated string.
 stable=[0]
 for j in range(1,len(ids)+1):
  s=tok.decode(ids[:j],skip_special_tokens=False,clean_up_tokenization_spaces=False)
  k=0
  while k<min(len(s),len(full)) and s[k]==full[k]:k+=1
  stable.append(k)
 assert all(a<=b for a,b in zip(stable,stable[1:])),stable
 selected=[];crossing=[]
 for j in range(len(ids)):
  a,b=stable[j],stable[j+1]
  if b==a:b=next((v for v in stable[j+2:] if v>a),a)
  if a>=start and b<=end and b>a and ids[j] not in tok.all_special_ids:selected.append(j)
  elif a<end and b>end or a<start and b>start:crossing.append(j)
 return dict(full_text=full,first_text=full[start:end].strip(),start_char=start,end_char=end,leading_reply_label_echo=echo,boundary=boundary,boundary_candidates=candidates,role_events=role_events,first_generated_local_indices=selected,boundary_crossing_token_indices=crossing)

def repeat(ids):
 grams=[tuple(ids[i:i+4]) for i in range(max(0,len(ids)-3))]
 return None if not grams else 1-len(set(grams))/len(grams)

def stats(r,positions):
 if not positions:return None
 L=str(len(r['temporal_rad']));h=r['lens'][L]['entropy_nats'];p=r['lens'][L]['pmax']
 return dict(n=len(positions),H_gen=float(np.mean([h[i-1] for i in positions])),pmax=float(np.mean([p[i-1] for i in positions])),temporal_rad=float(np.mean([r['mid_temp_rad'][i] for i in positions])),layer_one_minus_cos=float(np.mean([r['mid_layer_one_minus_cos'][i] for i in positions])))

def run_one(tok,model,spec,pad):
 prompt=spec['prompt'];q=spec['question'];c=spec['condition']
 token_ids=tok(prompt,add_special_tokens=False).input_ids
 assert not set(token_ids)&set(tok.all_special_ids),'Special token in input'
 assert '<|im_start|>' not in prompt and '<|im_end|>' not in prompt
 initial={}
 def head(m,a,out):
  if initial:return
  z=out.reshape(-1,out.shape[-1])[-1].float();lp=torch.log_softmax(z,-1);p=lp.exp();v=torch.topk(z,2)
  initial.update(H_next=float(-(p*lp).sum()),pmax=float(p.max()),top1_id=int(v.indices[0]),top1_text=tok.decode([int(v.indices[0])]),logit_gap=float(v.values[0]-v.values[1]))
 handle=model.lm_head.register_forward_hook(head)
 case=dict(id=spec['id'],exp='relation_tags',family=q['family'],group=c['id'],text=q['text'],max_new=160)
 if q.get('trigger'):case['trigger']=q['trigger']
 t=time.time();torch.cuda.reset_peak_memory_stats()
 try:r=core.run_case(PlainTokenizer(tok,prompt,pad),model,case,'')
 finally:handle.remove()
 assert r['token_ids'][:r['prompt_tokens']]==token_ids
 turn=parse_turn(tok,r['generated_token_ids'],c);firstpos=[r['prompt_tokens']+i for i in turn['first_generated_local_indices']]
 r['relation_spec']=spec;r['H_next_direct']=initial;r['turn']=turn
 r['first_turn_metrics']=stats(r,firstpos);r['full_metrics']=stats(r,r['spans']['generated'])
 r['first_turn_positions']=firstpos
 r['first_turn_repeat4']=repeat([r['token_ids'][i] for i in firstpos]);r['full_repeat4']=repeat([r['token_ids'][i] for i in r['spans']['generated']])
 r['H_conflict']=float(np.mean([r['lens'][str(len(r['temporal_rad']))]['entropy_nats'][i] for i in r['spans']['conflict']])) if 'conflict' in r['spans'] else None
 eos=model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else eos
 r['ended_with_eos']=bool(r['generated_token_ids'] and r['generated_token_ids'][-1] in eos)
 r['hit_limit']=len(r['generated_token_ids'])==160 and not r['ended_with_eos']
 r['first_turn_end_observed']=bool(turn['boundary'] or r['ended_with_eos'])
 r['input_special_token_ids']=sorted(set(token_ids)&set(tok.all_special_ids))
 r['output_special_ids']=[i for i in r['generated_token_ids'] if i in tok.all_special_ids]
 r['peak_cuda_allocated_GiB']=torch.cuda.max_memory_allocated()/1024**3;r['seconds']=time.time()-t
 return r

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--model',required=True);args=ap.parse_args();assert args.model in MODELS
 save_protocol();plan=cases();dest=ROOT/'raw'/args.model;dest.mkdir(parents=True,exist_ok=True)
 pending=[c for c in plan if not (dest/(c['id']+'.json')).exists()]
 if not pending:return
 torch.manual_seed(0);torch.set_num_threads(8)
 if args.model=='Qwen3-0.6B':tok,model=core.load_model(args.model);loadplan={};pad=151643;model.generation_config.eos_token_id=[151643,151645]
 else:tok,model,loadplan=load(args.model);pad=248044
 fingerprints={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'protocol.py',PARENT/'run_curvature_experiments.py',PARENT/'basepost/load_pair.py']}
 core.save(dest/'environment.json',dict(model=args.model,torch=torch.__version__,transformers=__import__('transformers').__version__,device=torch.cuda.get_device_name(),config=model.config.to_dict(),loadplan=loadplan,plain_text=True,code_fingerprints=fingerprints))
 for spec in pending:
  avail=int(memory()['MemAvailable'].split()[0])/1024**2;assert avail>14
  print('START',args.model,spec['id'],flush=True)
  r=run_one(tok,model,spec,pad);r['code_fingerprints']=fingerprints;core.save(dest/(spec['id']+'.json'),r)
  print('DONE',args.model,spec['id'],'sec',round(r['seconds'],2),'Hnext',r['H_next_direct']['H_next'],'first',r['turn']['first_text'],'BOUNDARY',r['turn']['boundary'],'repeat',r['first_turn_repeat4'],r['full_repeat4'],flush=True)
 del model,tok;drop();print('MODEL_COMPLETE',args.model,flush=True)
if __name__=='__main__':main()
