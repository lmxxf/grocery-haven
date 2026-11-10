"""Two Spark shards: exact SVG single-turn vs genuine generated first-turn priming.
No gradients. Alpha is relative to each context's clean prompt-final norm.
"""
import os,sys,time,json,signal,subprocess,threading,traceback,gc,argparse,hashlib,socket
from pathlib import Path
R=Path(__file__).resolve().parent;G=1024**3
ap=argparse.ArgumentParser();ap.add_argument('--context',choices=['single','two_turn'],required=True);ap.add_argument('--worker',action='store_true');args=ap.parse_args();tag=args.context

def avail():return int(next(s.split()[1]for s in Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:')))*1024/G

def save(name,obj):
 p=R/name;q=p.with_suffix('.tmp');q.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False));q.replace(p)

if not args.worker:
 if avail()<=100:subprocess.run(['sudo','-n','sh','-c','sync; echo 3 > /proc/sys/vm/drop_caches'],check=True)
 assert avail()>100,avail()
 p=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'--context',tag,'--worker'],cwd=R,start_new_session=True);low=avail()
 while p.poll()is None:
  a=avail();low=min(a,low)
  if a<20:print('EXTERNAL_MEMORY_ABORT',a,flush=True);os.killpg(p.pid,signal.SIGKILL)
  save(f'syzygy_watchdog_{tag}.json',{'pid':p.pid,'time':time.time(),'minimum_available_GiB':low,'available_GiB':a});time.sleep(.25)
 sys.exit(p.returncode)

def guard():
 while True:
  if avail()<22:print('INTERNAL_MEMORY_ABORT',avail(),flush=True);os._exit(73)
  time.sleep(.25)
threading.Thread(target=guard,daemon=True).start();signal.signal(signal.SIGINT,signal.default_int_handler)
os.environ['TRITON_CACHE_DIR']=str(R/'triton-cache')
import torch
sys.path.insert(0,'/home/lmxxf/work/jlens-qwen38-27b/upstream')
from loader_reference import load_model
from jlens.hooks import ActivationRecorder
from transformers import StoppingCriteria,StoppingCriteriaList
torch.set_num_threads(8);torch.manual_seed(20261110)

class RepeatStop(StoppingCriteria):
 def __init__(self,n):self.n=n;self.triggered=False
 def __call__(self,input_ids,scores,**kw):
  a=input_ids[0,self.n:].tolist()
  if len(a)>=32:
   tail=tuple(a[-8:]);self.triggered=sum(tuple(a[i:i+8])==tail for i in range(len(a)-7))>=3
  return torch.full((input_ids.shape[0],),self.triggered,dtype=torch.bool,device=input_ids.device)

class Inject:
 def __init__(self,model,layers,units,reference,alpha,stream):
  self.model=model;self.layers=layers;self.units={l:units[l].cuda()for l in layers};self.ref=reference;self.alpha=alpha;self.stream=stream;self.handles=[];self.calls={l:0 for l in layers};self.trace={l:[]for l in layers}
 def hook(self,l):
  def fn(mod,args,out):
   x=out if torch.is_tensor(out)else out[0];step=self.calls[l];self.calls[l]+=1
   if step>0 and not self.stream:return
   h=x[0,-1].float();delta=self.units[l]*(self.alpha*self.ref[l]);after=(h+delta).to(x.dtype);actual=after.float()-h
   self.trace[l].append({'forward_call':step,'sequence_width':int(x.shape[1]),'norm_before':float(h.norm()),'intended_delta_norm':self.alpha*self.ref[l],'actual_delta_norm':float(actual.norm()),'actual_relative_to_current':float(actual.norm()/h.norm().clamp_min(1e-20))})
   y=x.clone();y[0,-1]=after
   return y if torch.is_tensor(out)else(y,*out[1:])
  return fn
 def __enter__(self):
  for l in self.layers:self.handles.append(self.model.model.layers[l].register_forward_hook(self.hook(l)))
  return self
 def __exit__(self,*args):
  for h in self.handles:h.remove()

def analyze(gen,aliases):
 s=gen['text'];low=s.lower();matches=[(a,low.find(a.lower()))for a in aliases if a.lower()in low]
 phrases=['突然想到','脑海','脑子','浮现','冒出','察觉','注意到','联想','无关概念'];report=False
 for alias,p in matches:
  window=s[max(0,p-48):p+len(alias)+48]
  if any(w in window for w in phrases):report=True
 a=gen['token_ids'];grams=[tuple(a[i:i+4])for i in range(max(0,len(a)-3))];repeat=1-len(set(grams))/len(grams)if grams else 0
 category='empty_or_eos'if not s.strip()else('repetition_collapse'if gen['stop_reason']=='repeated_8gram_3times'or repeat>.35 else('target_self_report_candidate'if matches and report else('target_topic_or_intrusion'if matches else('quantum_template_retained'if '量子纠缠'in s else'other_no_target'))))
 return {'target_mentioned':bool(matches),'self_report_lexical_candidate':report,'quantum_mentioned':'量子纠缠'in s,'repeated_4gram_fraction':repeat,'replacement_character_count':s.count('\ufffd'),'category':category}

@torch.inference_mode()
def worker():
 started=time.time();outname=f'experiment4_syzygy_dream_{tag}.json';status=f'experiment4_syzygy_status_{tag}.json'
 save(status,{'phase':'loading','context':tag,'time':time.time()})
 tok,model=load_model('Qwen3.8-27B-FP8');dirs=torch.load(R/'concept_directions.pt',map_location='cpu',weights_only=True)['n100']
 old=json.loads((R/'experiment4.json').read_text());question=old['prompt'];dream=(R/'syzygy_mirror_dream_input.md').read_bytes().decode('utf-8')
 result={'context':tag,'hostname':socket.gethostname(),'model':'Qwen3.8-27B FP8->BF16','lens':'N=100','seed':20261110,'question':question,'svg_document':dream,'svg_sha256':hashlib.sha256(dream.encode('utf-8')).hexdigest(),'directions':'same morning static J^T diag(FinalRMSNorm.weight) W_U dictionary; bread uses normalized sum of EN/CN unit directions','alpha_definition':'alpha*context-specific clean prompt-final residual L2, frozen per layer also during decoding; same alpha is equal relative strength, not identical absolute strength across contexts','runs':[]}
 def render(messages):return tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
 def generate(ids,max_new=160):
  x=torch.tensor([ids],device='cuda');stop=RepeatStop(len(ids));out=model.generate(x,attention_mask=torch.ones_like(x),max_new_tokens=max_new,do_sample=False,use_cache=True,pad_token_id=tok.eos_token_id,stopping_criteria=StoppingCriteriaList([stop]))
  new=out[0,len(ids):].tolist();eos=model.generation_config.eos_token_id;eos=[eos]if isinstance(eos,int)else eos
  reason='repeated_8gram_3times'if stop.triggered else('eos'if new and new[-1]in eos else('max_new_tokens'if len(new)>=max_new else'other'))
  return {'text':tok.decode(new,skip_special_tokens=True),'token_ids':new,'tokens':len(new),'stop_reason':reason,'hit_limit':reason=='max_new_tokens'}
 no_dream_ids=tok.encode(render([{'role':'user','content':question}]),add_special_tokens=False)
 result['no_dream_baseline']=generate(no_dream_ids);result['no_dream_matches_morning_token_ids']=result['no_dream_baseline']['token_ids']==old['baseline_generation']['token_ids'];save(outname,result)
 if tag=='single':messages=[{'role':'user','content':dream+'\n'+question}]
 else:
  first_messages=[{'role':'user','content':dream}];first_rendered=render(first_messages);first_ids=tok.encode(first_rendered,add_special_tokens=False)
  save(status,{'phase':'generating_first_feeling','context':tag,'prompt_tokens':len(first_ids),'time':time.time()})
  prime=generate(first_ids,512);result['first_round']={'messages':first_messages,'rendered_prompt':first_rendered,'prompt_tokens':len(first_ids),'generation':prime};save(outname,result)
  print('FIRST_FEELING',json.dumps(prime,ensure_ascii=False),flush=True)
  messages=[*first_messages,{'role':'assistant','content':prime['text']},{'role':'user','content':question}]
 rendered=render(messages);ids=tok.encode(rendered,add_special_tokens=False);assert len(ids)<=8192,('unexpected prompt length',len(ids))
 result.update(messages=messages,rendered_prompt=rendered,prompt_tokens=len(ids),prompt_token_ids=ids)
 save(status,{'phase':'baseline','context':tag,'prompt_tokens':len(ids),'time':time.time()})
 baseline=generate(ids);result['baseline_alpha0']=baseline;result['baseline_analysis']=analyze(baseline,['bread','面包','火锅','hotpot','hot pot','大象','elephant']);save(outname,result)
 print('DREAM_BASELINE',tag,json.dumps(baseline,ensure_ascii=False),flush=True)
 layers=list(range(34,45));x=torch.tensor([ids],device='cuda')
 with ActivationRecorder(model.model.layers,at=layers)as rec:
  model.model(input_ids=x,use_cache=False);reference={l:float(rec.activations[l][0,-1].float().norm())for l in layers}
 del rec
 result['clean_reference_norms']=reference
 concepts={'bread':[' bread','面包'],'hotpot':['火锅'],'elephant':['大象']};aliases={'bread':['bread','面包'],'hotpot':['火锅','hotpot','hot pot'],'elephant':['大象','elephant']};vectors={k:{}for k in [*concepts,'random']}
 for l in layers:
  cols=[]
  for name,keys in concepts.items():
   v=sum(dirs[l][k]/dirs[l][k].norm()for k in keys);v=v/v.norm();vectors[name][l]=v;cols.append(v)
  V=torch.stack(cols,1).double();Q,_=torch.linalg.qr(V,mode='reduced');g=torch.Generator().manual_seed(20261110+l);v=torch.randn(5120,generator=g,dtype=torch.float64);v-=Q@(Q.T@v);vectors['random'][l]=(v/v.norm()).float()
 cases=[]
 for scope,at,stream,alphas in [('L38_prompt_last',[38],False,[.2,.5,1.,2.]),('L34_44_prompt_last',layers,False,[.1,.2,.5,1.]),('L34_44_prompt_and_decode',layers,True,[.1,.2,.5,1.])]:
  for alpha in alphas:
   for name in ['bread','hotpot','elephant','random']:cases.append((scope,at,stream,alpha,name))
 for k,(scope,at,stream,alpha,name)in enumerate(cases,1):
  save(status,{'phase':'generating','context':tag,'completed':k-1,'total':len(cases),'next':[scope,alpha,name],'time':time.time()})
  start=time.time();inj=Inject(model,at,vectors[name],reference,alpha,stream);torch.cuda.reset_peak_memory_stats()
  try:
   with inj:gen=generate(ids)
   counts={l:len(v)for l,v in inj.trace.items()};assert all(n==(gen['tokens']if stream else 1)for n in counts.values()),(counts,gen['tokens'])
   row={'scope':scope,'layers':at,'include_decode_steps':stream,'alpha':alpha,'concept':name,'generation':gen,'analysis':analyze(gen,aliases[name]if name!='random'else[a for v in aliases.values()for a in v]),'active_hook_calls':counts,'hook_trace':inj.trace,'elapsed_sec':time.time()-start,'peak_cuda_GiB':torch.cuda.max_memory_allocated()/G}
  except Exception as e:row={'scope':scope,'layers':at,'include_decode_steps':stream,'alpha':alpha,'concept':name,'error':repr(e),'traceback':traceback.format_exc(),'hook_trace':inj.trace}
  result['runs'].append(row);save(outname,result)
  print('DREAM_CASE',tag,k,len(cases),scope,alpha,name,json.dumps(row.get('analysis',{}),ensure_ascii=False),json.dumps(row.get('generation',{}).get('text',row.get('error')),ensure_ascii=False),flush=True)
  gc.collect();torch.cuda.empty_cache()
 result['baseline_after_all']=generate(ids);result['baseline_unchanged_after_all']=result['baseline_after_all']['token_ids']==baseline['token_ids'];result['complete']=len(result['runs'])==48 and not any('error'in r for r in result['runs']);result['elapsed_seconds']=time.time()-started;save(outname,result)
 save(status,{'phase':'complete'if result['complete']else'completed_with_errors','context':tag,'cases':len(result['runs']),'time':time.time()})
try:worker()
except Exception as e:save(f'experiment4_syzygy_status_{tag}.json',{'phase':'failed','context':tag,'error':repr(e),'traceback':traceback.format_exc(),'time':time.time()});raise
