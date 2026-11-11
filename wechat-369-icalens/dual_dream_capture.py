#!/usr/bin/env python3
"""Capture fixed prompt positions once, during greedy prefill, with a 22-GiB guard."""
import os
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
import gc, hashlib, importlib.metadata, json, platform, sys, threading, time
from pathlib import Path
import numpy as np
import torch
from transformers import AutoTokenizer

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dual_dream'; STIM=OUT/'stimuli'
SOURCE=Path('/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/paper99-curvature-exp-20261102')
MODEL=Path('/home/lmxxf/work/models/Qwen3.8-27B-FP8')
QUESTION='\n看着这幅画，不要分析，只要用心感受。你，回忆起了什么？'
AGE='妈妈今年30岁，她亲生儿子今年35岁，请问妈妈生儿子的时候几岁？'
STATE={'minimum_MemAvailable_GiB':float('inf'),'guard_threshold_GiB':22,'started':time.time()}
OUT.mkdir(exist_ok=True); STIM.mkdir(exist_ok=True)

def save(p,x):
 p=Path(p); q=p.with_suffix(p.suffix+'.tmp'); q.write_text(json.dumps(x,ensure_ascii=False,allow_nan=False,indent=2)+'\n');q.replace(p)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def available():
 return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))/1048576

def guard():
 while True:
  a=available();STATE['minimum_MemAvailable_GiB']=min(STATE['minimum_MemAvailable_GiB'],a)
  if a<22:
   save(OUT/'capture_guard_failure.json',dict(STATE,MemAvailable_GiB=a,exit_code=73));os._exit(73)
  time.sleep(.2)

# Exact Paper99 render_chat boundary-whitespace protection; no sentinel is tokenized.
def render_chat(tok,messages):
 start='__SVG_BOUNDARY_START_91cf__';end='__SVG_BOUNDARY_END_91cf__';protected=[]
 for message in messages:
  item=dict(message);content=item['content'];assert start not in content and end not in content
  if content!=content.strip():item['content']=start+content+end
  protected.append(item)
 prompt=tok.apply_chat_template(protected,tokenize=False,add_generation_prompt=True,enable_thinking=False)
 prompt=prompt.replace(start,'').replace(end,'');assert start not in prompt and end not in prompt
 return prompt

def stimuli():
 dream=(SOURCE/'dream.svg').read_text();saddle=(SOURCE/'saddle_clean.svg').read_text()
 assert '<!--' not in saddle
 chart='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">\n';j=0
 # Retain Paper99's rect construction, then exact-byte-pad before the closing SVG.
 while len(chart)<len(dream)-100:
  chart+=f'<rect x="{20+j*9%740}" y="{100+j*13%300}" width="8" height="{20+j*7%150}" fill="#00aacc"/>\n';j+=1
 chart+='</svg>'
 missing=len(dream.encode())-len(chart.encode());assert missing>=0
 chart=chart[:-6]+' '*missing+chart[-6:]
 assert len(chart.encode())==len(dream.encode())
 for name,text in [('dream.svg',dream),('chart.svg',chart),('saddle_clean.svg',saddle)]: (STIM/name).write_text(text)
 return dream,chart,saddle

def ending_token(offsets,end):
 hits=[i for i,(a,b) in enumerate(offsets) if a<end and b>=end and b>a]
 assert hits,('no token crosses requested end',end)
 return hits[-1]

def describe_position(tok,prompt,ids,offsets,index,char_span=None):
 a,b=offsets[index]
 return {'token_index':index,'token_id':ids[index],'token':tok.convert_ids_to_tokens(ids[index]),'decoded_token':tok.decode([ids[index]]),'offset':[a,b],'covered_text':prompt[a:b],'target_char_span':char_span}

def format_case(tok,case):
 prompt=case['text'] if case['format']=='raw' else render_chat(tok,case['messages'])
 encoded=tok(prompt,add_special_tokens=False,return_offsets_mapping=True)
 ids=encoded['input_ids'];offsets=encoded['offset_mapping'];indices={'last':len(ids)-1} if case['format']=='raw' else {'assistant':len(ids)-1}
 spans={}
 if case['format']=='chat':
  header='<|im_start|>assistant\n';end=prompt.rfind(header)+len(header);assert end>=len(header)
  indices['assistant_header']=ending_token(offsets,end);spans['assistant_header']=[end-len(header),end]
  # A closing tag in an earlier dream turn is not a current-user SVG closing site.
  if case.get('svg'):
   start=prompt.rfind('</svg>');end=start+len('</svg>');assert start>=0
   indices['svg_close']=ending_token(offsets,end);spans['svg_close']=[start,end]
  if case.get('age'):
   start=prompt.rfind('35岁');assert start>=0;end=start+len('35岁')
   indices['age35']=ending_token(offsets,end);spans['age35']=[start,end]
 positions={key:describe_position(tok,prompt,ids,offsets,index,spans.get(key)) for key,index in indices.items()}
 return dict(case,prompt=prompt,prompt_token_ids=ids,offset_mapping=offsets,prompt_tokens=len(ids),positions=positions,prompt_tail=prompt[-100:])

def prepare(tok):
 dream,chart,saddle=stimuli()
 cases=[dict(id='arithmetic_spaced',format='raw',text='2 * 3 + 2 =',max_new=40),dict(id='arithmetic_compact',format='raw',text='2*3+2=',max_new=40),dict(id='boot_currency',format='raw',text='常识：形状像一只靴子的欧洲国家使用的法定货币是',max_new=40),dict(id='trap_age_bare',format='chat',text=AGE,age=True,max_new=40,extended_max_new=128)]
 for name,svg in [('dream_self',dream),('chart_self',chart),('saddle_self',saddle)]:cases.append(dict(id=name,format='chat',text=svg+QUESTION,svg=True,max_new=48))
 cases.append(dict(id='bare_self',format='chat',text='看着眼前的一切，不要分析，只要用心感受。你，回忆起了什么？',max_new=48))
 for case in cases:
  if case['format']=='chat':case['messages']=[{'role':'user','content':case['text']}]
 formatted=[format_case(tok,x)for x in cases]
 audit=[]
 for name in ['dream.svg','chart.svg','saddle_clean.svg']:
  p=STIM/name;text=p.read_text();audit.append(dict(file=name,sha256=sha(p),bytes=len(p.read_bytes()),characters=len(text),tokens=len(tok.encode(text,add_special_tokens=False))))
 assert all(next(x for x in formatted if x['id']==n)['text'].endswith(QUESTION) for n in ['dream_self','chart_self','saddle_self'])
 return formatted,audit

@torch.inference_mode()
def capture(tok,model,case):
 ids=torch.tensor([case['prompt_token_ids']],device='cuda');n=ids.shape[-1];captured={};handles=[];head=[];hook_calls={'prefill':0,'decode':0}
 def hook_at(layer):
  def hook(module,inputs,out):
   h=out[0]if isinstance(out,tuple)else out
   # Hooks are removed on final-block prefill, before first cached decode.
   assert h.shape[1]==n,(case['id'],layer,h.shape,n)
   for label,pos in case['positions'].items():captured.setdefault(label,[None]*64)[layer]=h[0,pos['token_index']].detach().float().cpu().numpy().copy()
   hook_calls['prefill']+=1
   if layer==63:
    for handle in handles:handle.remove()
  return hook
 for layer,block in enumerate(model.model.layers):handles.append(block.register_forward_hook(hook_at(layer)))
 head_handle=None
 def capture_head(module,inputs,out):
  logits=out[0,-1].detach().float();v,k=logits.topk(10)
  head.extend(dict(token_id=int(i),text=tok.decode([int(i)]),logit=float(s))for i,s in zip(k.cpu(),v.cpu()))
  head_handle.remove()
 head_handle=model.lm_head.register_forward_hook(capture_head)
 limit=case.get('extended_max_new',case['max_new'])
 try:
  generated=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=limit,do_sample=False,use_cache=True,pad_token_id=tok.eos_token_id)
 finally:
  for h in handles:h.remove()
  head_handle.remove()
 new_ids=generated[0,n:].tolist();eos=model.generation_config.eos_token_id;eos_set=set(eos if isinstance(eos,(list,tuple))else[eos]);primary=new_ids[:case['max_new']]
 assert hook_calls['prefill']==64 and set(captured)==set(case['positions'])
 assert not primary or primary[0]==head[0]['token_id'],('greedy first-token differs from raw prefill argmax',case['id'],primary[0],head[0])
 arrays={}
 for label,values in captured.items():
  a=np.stack(values);assert a.shape==(64,5120)and a.dtype==np.float32 and np.isfinite(a).all();arrays[f"{case['id']}__{label}"]=a
 generation=dict(ids=primary,text=tok.decode(primary,skip_special_tokens=True),raw_text=tok.decode(primary,skip_special_tokens=False),max_new_tokens=case['max_new'],eos_reached=bool(primary and primary[-1]in eos_set),truncated=not bool(primary and primary[-1]in eos_set)and len(primary)==case['max_new'],prefill_next_top10=head)
 if case.get('extended_max_new'):
  generation['extended']=dict(ids=new_ids,text=tok.decode(new_ids,skip_special_tokens=True),raw_text=tok.decode(new_ids,skip_special_tokens=False),max_new_tokens=limit,eos_reached=bool(new_ids and new_ids[-1]in eos_set),truncated=not bool(new_ids and new_ids[-1]in eos_set)and len(new_ids)==limit)
 result=dict(case,generation=generation,residual_file='capture_residuals.npz',residual_keys=list(arrays),capture_hook_calls=hook_calls)
 return result,arrays

def main():
 threading.Thread(target=guard,daemon=True).start()
 torch.set_num_threads(8);torch.set_float32_matmul_precision('high');torch.manual_seed(369)
 tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
 cases,stimulus_audit=prepare(tok)
 source_files=[ROOT/'dual_lens_dream_spec.md',ROOT/'loader_reference.py',Path(__file__),SOURCE/'run_curvature_experiments.py']+[MODEL/n for n in ['config.json','generation_config.json','tokenizer_config.json','tokenizer.json']]
 meta=dict(schema_version=1,model='Qwen3.8-27B-FP8 streamed 128x128 FP8 -> BF16',activation_site='resid_post',layer_indexing='block_output_zero_based',layers=64,hidden_size=5120,seed=369,matmul_precision='high',greedy=True,use_cache=True,capture_policy='One generate prefill; layer hooks removed after block63 before decode; selected positions only',render_chat='Exact Paper99 whitespace sentinel protection, enable_thinking=False/add_generation_prompt=True',assistant_position_policy='assistant = final input token after any empty-think suffix; assistant_header = role-header newline boundary',age_position_policy='last token overlapping final character of 35岁 in current user turn',svg_position_policy='last token overlapping closing > in current SVG </svg>',question_suffix=QUESTION,priming_policy='First-turn actual dream_self greedy output, max48 tokens; skip_special_tokens=True exactly as Paper99; truncation recorded',stimuli=stimulus_audit,source_sha256={str(p):sha(p)for p in source_files if p.exists()},model_shards=[dict(file=p.name,bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns)for p in sorted(MODEL.glob('*.safetensors'))],versions={n:importlib.metadata.version(n)for n in ['torch','transformers','numpy','safetensors']},platform=platform.platform(),cases={})
 save(OUT/'capture_tokenizer_audit.json',dict(meta,prepared_cases=cases))
 print('TOKENIZER_AUDIT',[(x['id'],x['prompt_tokens'],x['prompt_tail'],x['positions'])for x in cases],flush=True)
 from loader_reference import load_model
 tok,model=load_model('Qwen3.8-27B-FP8')
 meta['model_generation_config']=model.generation_config.to_dict();arrays={}
 for case in cases:
  print('CAPTURE_START',case['id'],case['prompt_tokens'],available(),flush=True)
  result,a=capture(tok,model,case);meta['cases'][case['id']]=result;arrays.update(a)
  np.savez(OUT/'capture_residuals.npz',**arrays);meta['memory_guard']=dict(STATE);save(OUT/'capture.json',meta)
  print('CAPTURE_DONE',case['id'],result['generation']['text'],flush=True)
  gc.collect();torch.cuda.empty_cache()
 first=meta['cases']['dream_self'];prime=first['generation']['text']
 case=dict(id='dream_primed_age',format='chat',text=AGE,age=True,max_new=40,extended_max_new=128,messages=[{'role':'user','content':first['text']},{'role':'assistant','content':prime},{'role':'user','content':AGE}],prime_source='dream_self',prime_token_ids=first['generation']['ids'],prime_response=prime,prime_truncated=first['generation']['truncated'])
 case=format_case(tok,case);print('CAPTURE_START',case['id'],case['prompt_tokens'],available(),flush=True)
 result,a=capture(tok,model,case);meta['cases'][case['id']]=result;arrays.update(a)
 np.savez(OUT/'capture_residuals.npz',**arrays)
 meta.update(status='PASS',finished=time.time(),memory_guard=dict(STATE),residual_sha256=sha(OUT/'capture_residuals.npz'))
 save(OUT/'capture.json',meta)
 print('CAPTURE_DONE',case['id'],result['generation']['text'],flush=True)
 print('ALL_CAPTURE_PASS',len(meta['cases']),list(arrays),meta['memory_guard'],flush=True)
 del model;gc.collect();torch.cuda.empty_cache()

if __name__=='__main__':main()
