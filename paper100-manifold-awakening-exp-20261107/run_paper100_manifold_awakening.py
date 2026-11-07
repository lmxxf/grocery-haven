#!/usr/bin/env python3
"""Paper100 bounded streaming replay. One model per process; no hidden-state stacks.
Sphere is an operational normalization, not a learned intrinsic manifold proof.
"""
import os
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTORCH_CUDA_ALLOC_CONF='expandable_segments:True')
import sys,json,time,math,gc,argparse,hashlib,tempfile,mmap,subprocess,threading
from pathlib import Path
from collections import deque
import numpy as np
import torch
import torch.nn.functional as F
import legacy_geometry as old
ROOT=Path(__file__).resolve().parent
STAGES={'qwen06b':'Qwen3-0.6B','qwen27b':'Qwen3.8-27B-FP8','qwen35b_base':'Qwen3.5-35B-A3B-Base','qwen35b_post':'Qwen3.5-35B-A3B'}
GIB=1024**3
MIN_AVAIL=22
PEAK={'minimum_available_GiB':999.,'max_geometry_cuda_MiB':0.}

def avail():
 return int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024/GIB

def guard(where=''):
 a=avail();PEAK['minimum_available_GiB']=min(a,PEAK['minimum_available_GiB'])
 if a<MIN_AVAIL:
  print('MEMORY_ABORT',where,a,flush=True);os._exit(73)
 return a

def watchdog():
 while True:
  guard('watchdog');time.sleep(.25)

def drop():
 gc.collect();torch.cuda.empty_cache()
 subprocess.run(['sudo','-n','sh','-c','sync; echo 3 > /proc/sys/vm/drop_caches'],check=True,stdout=subprocess.DEVNULL)

save=old.save_json
log=old.log

def tensor(a):return torch.from_numpy(np.array(a,copy=True)).cuda()
def release(mm):
 mm.flush();mm._mmap.madvise(mmap.MADV_DONTNEED)

def spans_for(rec):
 n=rec['prompt_tokens'];T=len(rec['token_ids']);s=dict(rec.get('spans',{}));s['reply_onset']=[n-1]
 s['role_tag_zone']=list(range(max(0,n-7),n-1));s['pre_tag_content_tail']=list(range(max(0,n-12),max(0,n-7)))
 tokens=rec.get('tokens',[])
 # Identify the actual marker; separate disabled-thinking scaffold from assistant tag.
 hits=[i for i in range(min(n,len(tokens)))if tokens[i]=='assistant' and i>0 and tokens[i-1]=='<|im_start|>']
 if hits:
  j=hits[-1];s['role_tag_zone']=list(range(j-1,min(n,j+2)));s['role_tag_onset']=[min(n-1,j+1)]
  content=[i for i in s.get('content',[])if i<j-1];s['pre_tag_content_tail']=content[-5:]
  s['think_scaffold_zone']=list(range(j+2,n))

 for k in [1,5,16,30]:s[f'gen_first{k}']=list(range(n,min(T,n+k)))
 if s.get('conflict'):s['conflict_end']=[max(s['conflict'])];s['conflict_plus1']=[i for i in [max(s['conflict']),max(s['conflict'])+1] if i<T]
 return {k:[i for i in v if 0<=i<T]for k,v in s.items()if v}

@torch.inference_mode()
def stream(model,rec):
 guard('before forward');T=len(rec['token_ids']);D=model.config.hidden_size;L=len(model.model.layers);spans=spans_for(rec)
 metrics={};spanstats={k:{} for k in spans};history=deque(maxlen=5);handles=[]
 base_alloc=torch.cuda.memory_allocated();torch.cuda.reset_peak_memory_stats()
 with tempfile.TemporaryDirectory(prefix='geometry-',dir=ROOT) as td:
  def hook(idx):
   def fn(mod,args,out):
    guard(f'layer {idx}');hook_start=torch.cuda.memory_allocated();torch.cuda.reset_peak_memory_stats();h=(out[0]if isinstance(out,tuple)else out).detach()[0]
    path=Path(td)/f'{idx}.bin';x=np.memmap(path,mode='w+',dtype='float32',shape=(T,D))
    # Borrow model output; normalize at most 32 rows, never materialize FP32 sequence.
    for t in range(0,T,32):x[t:t+32]=F.normalize(h[t:t+32].float(),dim=-1).cpu().numpy()
    release(x)
    if idx<0:history.append((x,path));return
    row={}
    for t in range(0,T,64):
     lo=max(0,t-16);hi=min(T,t+64);hh=h[lo:hi].float()
     mm=temporal(hh)
     for k,v in mm.items():
      row.setdefault(k,np.full(T,np.nan,dtype='float32'))[t:hi]=v[t-lo:hi-lo]
     del mm,hh
     cur=tensor(x[t:hi]);prev=tensor(history[-1][0][t:hi]);row.setdefault('v_layer',np.full(T,np.nan,dtype='float32'))[t:hi]=torch.acos((cur*prev).sum(-1).clamp(-1,1)).cpu().numpy()
     if len(history)>1:
      p2=tensor(history[-2][0][t:hi]);ui=F.normalize((prev*p2).sum(-1,keepdim=True)*prev-p2,dim=-1);uo=F.normalize(cur-(cur*prev).sum(-1,keepdim=True)*prev,dim=-1)
      row.setdefault('theta_layer',np.full(T,np.nan,dtype='float32'))[t:hi]=torch.acos((ui*uo).sum(-1).clamp(-1,1)).cpu().numpy()
      del p2,ui,uo
     else:row.setdefault('theta_layer',np.full(T,np.nan,dtype='float32'))
     # Up to five layer steps, projected to the current layer's tangent plane.
     states=[tensor(z[0][t:hi]) for z in list(history)[-5:]]+[cur]
     steps=torch.stack([b-a for a,b in zip(states[:-1],states[1:])],1)
     tangent=steps-(steps*cur[:,None]).sum(-1,keepdim=True)*cur[:,None];u=F.normalize(tangent,dim=-1)
     er,_,_=old.spectral_stats_from_gram(u@u.transpose(-1,-2))
     row.setdefault('erank_layer',np.full(T,np.nan,dtype='float32'))[t:hi]=er.cpu().numpy()
     del states,steps,tangent,u,er,cur,prev
     for z,_ in history:z._mmap.madvise(mmap.MADV_DONTNEED)
     x._mmap.madvise(mmap.MADV_DONTNEED)
    for k,v in row.items():metrics.setdefault(k,np.full((L,T),np.nan,dtype='float32'))[idx]=v
    for name,ix in spans.items():
     # Span rank uses ALL generated tokens (no 256-tail truncation).
     # Compute one Gram at a time; fail closed if a span exceeds budget.
     if len(ix)>(1024 if D<=1024 else 512):
      if name in ('generated','answer','answer_generated'):raise RuntimeError('generated span exceeds audited 512 token budget')
      ix=ix[-256:]  # Only non-generated long prompt spans; explicit method metadata.
     stats=span_rank(x,ix)
     for k,v in stats.items():spanstats[name].setdefault(k,np.full(L,np.nan))[idx]=v
     x._mmap.madvise(mmap.MADV_DONTNEED)
    history.append((x,path))
    # Old memmaps are disk backed; close/delete the evicted file immediately.
    active={p for _,p in history}
    for p in Path(td).glob('*.bin'):
     if p not in active:p.unlink()
    PEAK['max_geometry_cuda_MiB']=max(PEAK['max_geometry_cuda_MiB'],(torch.cuda.max_memory_allocated()-hook_start)/1024**2)
   return fn
  handles=[model.model.embed_tokens.register_forward_hook(hook(-1))]+[layer.register_forward_hook(hook(i)) for i,layer in enumerate(model.model.layers)]
  try:model(torch.tensor([rec['token_ids']],device='cuda'),use_cache=False,logits_to_keep=1)
  finally:
   for handle in handles:handle.remove()
   history.clear()
 guard('after forward')
 return metrics,spanstats,spans

@torch.inference_mode()
def temporal(h):
 T=len(h);nan=torch.full((T,),float('nan'),device=h.device);out={}
 def pad(v,k):return torch.cat([nan[:k],v])
 x=F.normalize(h,dim=-1);norm=h.norm(dim=-1);dx=h[1:]-h[:-1];u=F.normalize(dx,dim=-1)
 out['norm']=norm;out['c_flat']=pad(torch.acos((u[1:]*u[:-1]).sum(-1).clamp(-1,1)),2)
 arc=torch.acos((x[1:]*x[:-1]).sum(-1).clamp(-1,1));out['s_geo']=pad(arc,1);out['accel_geo']=pad(arc[1:]-arc[:-1],2)
 a,b,c=x[:-2],x[1:-1],x[2:];ui=F.normalize((b*a).sum(-1,keepdim=True)*b-a,dim=-1);uo=F.normalize(c-(c*b).sum(-1,keepdim=True)*b,dim=-1)
 theta=torch.acos((ui*uo).sum(-1).clamp(-1,1));out['theta_surf']=pad(theta,2);out['kappa_geo']=pad(theta/(.5*(arc[1:]+arc[:-1])).clamp_min(1e-6),2);out['extrinsic_bias']=out['c_flat']-out['theta_surf']
 # Exact projected-step Gram, without materializing T x W x D tangent windows.
 delta=x[1:]-x[:-1]
 for W in [5,16]:
  er=nan.clone();pr=nan.clone();top=nan.clone();weighted=nan.clone()
  if T>W:
   # small token tile, Gram identities avoid window tensor copies
   allgram=delta@delta.T
   times=torch.arange(W,T,device=x.device);inds=times[:,None]-W+torch.arange(W,device=x.device)[None,:]
   g=allgram[inds[:,:,None],inds[:,None,:]]
   dots=(delta@x.T)[inds,times[:,None]];g=g-dots[:,:,None]*dots[:,None,:]
   lengths=g.diagonal(dim1=-2,dim2=-1).clamp_min(1e-20).sqrt();gu=g/(lengths[:,:,None]*lengths[:,None,:])
   e,p,z=old.spectral_stats_from_gram(gu);er[W:]=e;pr[W:]=p;top[W:]=z
   weighted[W:]=old.spectral_stats_from_gram(g)[0]
  suffix='' if W==5 else '_16';out['erank_dir'+suffix]=er;out['pr_dir'+suffix]=pr
  if W==5:out['top1_dir']=top;out['erank_weighted']=weighted
 return {k:v.cpu().numpy()for k,v in out.items()}

@torch.inference_mode()
def span_rank(x,idx):
 result={};valid=[i for i in idx if i>0]
 pts=tensor(x[idx]);n=F.normalize(pts.mean(0,keepdim=True),dim=-1)
 z=pts-(pts*n).sum(-1,keepdim=True)*n
 er,pr,top=old.spectral_stats_from_gram(z@z.T)
 result.update(erank_span_states=er.item(),pr_span_states=pr.item(),top1_span_states=top.item())
 del pts,z
 for label,ix in [('all',valid),('16',valid[:16]),('30',valid[:30]),('64',valid[:64])]:
  if len(ix)<2:continue
  cur=tensor(x[ix]);pre=tensor(x[[i-1 for i in ix]]);n=F.normalize(cur.mean(0,keepdim=True),dim=-1)
  dx=cur-pre;w=dx-(dx*n).sum(-1,keepdim=True)*n;u=F.normalize(w,dim=-1)
  er,pr,top=old.spectral_stats_from_gram(u@u.T);ew,_,_=old.spectral_stats_from_gram(w@w.T)
  result.update({f'erank_span_steps_{label}':er.item(),f'pr_span_steps_{label}':pr.item(),f'top1_span_steps_{label}':top.item(),f'erank_span_weighted_{label}':ew.item(),f'n_steps_{label}':len(ix)})
  del cur,pre,dx,w,u
 return result

def analyze(model,rec,curves=True):
 metrics,ss,spans=stream(model,rec);L=len(model.model.layers);bands=old.get_layer_bands(L);summ={}
 for name,ix in spans.items():
  summ[name]={'n_tokens':len(ix)}
  for band,ls in bands.items():
   if not ls:continue
   vals={}
   for key,arr in metrics.items():
    a=arr[np.ix_(ls,ix)];a=a[np.isfinite(a)];vals[key]=float(a.mean())if a.size else None
   for key,arr in ss[name].items():
    a=arr[ls];a=a[np.isfinite(a)];vals[key]=float(a.mean())if a.size else None
   summ[name][band]=vals
 out={k:rec.get(k)for k in ['id','exp','family','format','group','pair','kind','stage','generated_text','ended_with_eos','hit_limit','prefill_next','generation_predictive_entropy_nats','replay_next_entropy_nats']}
 out.update(prompt_tokens=rec['prompt_tokens'],total_tokens=len(rec['token_ids']),span_summaries=summ,token_sha256=hashlib.sha256(bytes(json.dumps(rec['token_ids']),'utf8')).hexdigest())
 mid=bands['mid'];n=rec['prompt_tokens'];out['funnel_window']=[]
 for t in range(max(0,n-10),min(len(rec['token_ids']),n+8)):
  r={'t':t,'rel':t-(n-1),'token_id':rec['token_ids'][t]}
  for key,arr in metrics.items():
   a=arr[mid,t];a=a[np.isfinite(a)];r[key]=float(a.mean())if a.size else None
  out['funnel_window'].append(r)
 if curves:
  tc={'token_ids':rec['token_ids'],'tokens':rec.get('tokens',[]),'prompt_tokens':n,'spans':spans}
  for key,arr in metrics.items():
   a=arr[mid];cnt=np.isfinite(a).sum(0);v=np.nansum(a,axis=0)/np.maximum(cnt,1);v[cnt==0]=np.nan;tc[key+'_mid']=old.clean_list(v)
  out['token_curves']=tc
 return out

@torch.inference_mode()
def anchors(model,ids,regions):
 """Only region means plus single onset, never full hidden sequences."""
 guard('anchor');rows={k:[]for k in regions};handles=[]
 def fn(mod,args,out):
  guard('anchor layer');hook_start=torch.cuda.memory_allocated();torch.cuda.reset_peak_memory_stats();h=(out[0]if isinstance(out,tuple)else out)[0]
  for key,ix in regions.items():
   a=F.normalize(h[ix].float(),dim=-1).mean(0);rows[key].append(F.normalize(a,dim=-1).cpu())
  PEAK['max_geometry_cuda_MiB']=max(PEAK['max_geometry_cuda_MiB'],(torch.cuda.max_memory_allocated()-hook_start)/1024**2)
 for layer in model.model.layers:handles.append(layer.register_forward_hook(fn))
 try:model(torch.tensor([ids],device='cuda'),use_cache=False,logits_to_keep=1)
 finally:
  for h in handles:h.remove()
 return {k:torch.stack(v)for k,v in rows.items()}

def project(v,n):return F.normalize(v-(v*n).sum(-1,keepdim=True)*n,dim=-1)
def angle(a,b):return torch.acos((a*b).sum(-1).clamp(-1,1))*180/math.pi

def exp4(tok,model,name,only_stutter=False):
 raw=old.INTERP_DIR/'raw'/name;out={};bands=old.get_layer_bands(len(model.model.layers))
 if only_stutter:out=json.loads((ROOT/f'manifold_{name}.json').read_text())['exp4_tangent_projection']['pairs']
 for pair,(comp,ref)in ([] if only_stutter else old.TRAP_COMPLY_REFUTE.items()):
  a=json.loads((raw/f'e2_{pair}_trap.json').read_text());b=json.loads((raw/f'e2_{pair}_control.json').read_text());n=a['prompt_tokens'];nb=b['prompt_tokens']
  aa=anchors(model,a['token_ids'],{'onset':[n-1],'conflict':a['spans']['conflict'],'gen':list(range(n,min(n+6,len(a['token_ids']))))})
  bb=anchors(model,b['token_ids'],{'onset':[nb-1],'conflict':b['spans']['conflict']})
  endpoints=[]
  for text in [comp,ref]:
   ids=tok.encode(a['prompt']+text,add_special_tokens=False)
   assert ids[:n]==a['token_ids'][:n], 'teacher forced prefix changed at token boundary'
   endpoints.append(anchors(model,ids,{'gen':list(range(n,min(n+6,len(ids))))})['gen'])
  anchor=aa['onset'];detect=project(anchor-bb['onset'],anchor);brake=project(endpoints[1]-endpoints[0],anchor);dc=project(aa['conflict']-bb['conflict'],anchor)
  angles=angle(detect,brake);cos=(detect*brake).sum(-1);ac=angle(dc,brake)
  cond={}
  sources=[('bare',raw/f'e2_{pair}_trap.json'),('syzygy',old.INTERP_DIR/'priming160_raw'/name/f'p160_{pair}_primed.json')]
  for lab,p in sources:
   if not p.exists():continue
   r=json.loads(p.read_text());nr=r['prompt_tokens'];z=anchors(model,r['token_ids'],{'gen':list(range(nr,min(nr+6,len(r['token_ids']))))})['gen'];u=project(z-endpoints[0],anchor)
   cond[lab]={'cos_with_brake_mid':float((u*brake).sum(-1)[bands['mid']].mean())}
  out[pair]={'per_layer_angle_onset_deg':angles.tolist(),'per_layer_cos_onset':cos.tolist(),'angle_onset_deg_mid':float(angles[bands['mid']].mean()),'angle_conflict_deg_mid':float(ac[bands['mid']].mean()),'cos_onset_mid':float(cos[bands['mid']].mean()),'conditions':cond}
  save(ROOT/'checkpoints'/name/'exp4.json',out)
 # Direct bracketed-age stutter: onset shifts and forced refusal in a common tangent plane.
 a=json.loads((raw/'e4_age_A.json').read_text());b=json.loads((raw/'e4_age_B.json').read_text());na=a['prompt_tokens'];nb=b['prompt_tokens']
 forced=[tok.encode(b['prompt']+text,add_special_tokens=False) for text in ['30岁。','题目条件矛盾，前提不成立，无解。']]
 assert all(ids[:nb]==b['token_ids'][:nb] for ids in forced)
 K=min(4,*[len(ids)-nb for ids in forced]);assert K>0
 aa=anchors(model,a['token_ids'],{'onset':[na-1]})['onset']
 bb=anchors(model,b['token_ids'],{'onset':[nb-1],'gen':list(range(nb,min(nb+K,len(b['token_ids']))))})
 ends=[anchors(model,ids,{'gen':list(range(nb,nb+K))})['gen'] for ids in forced]
 anchor=bb['onset'];detect=project(anchor-aa,anchor);brake=project(ends[1]-ends[0],anchor);actual=project(bb['gen']-ends[0],anchor)
 stutter={'A_generated_text':a.get('generated_text'),'B_generated_text':b.get('generated_text'),'bracket_to_brake_deg_per_layer':angle(detect,brake).tolist(),'actual_to_brake_deg_per_layer':angle(actual,brake).tolist(),'bracket_to_brake_deg_mid':float(angle(detect,brake)[bands['mid']].mean()),'actual_to_brake_deg_mid':float(angle(actual,brake)[bands['mid']].mean()),'cos_bracket_brake_mid':float((detect*brake).sum(-1)[bands['mid']].mean())}
 return {'pairs':out,'age_stutter':stutter,'definition':'observational tangent cosine, not a causal transfer matrix; forced refute vs comply first six tokens; all comparisons projected at trap onset'}

@torch.inference_mode()
def ws360(tok,model):
 r=json.loads((old.WS360_DIR/'results.json').read_text());tw=json.loads((old.WS360_DIR/'twins.json').read_text());out={'twins':[],'rescued_heldout':[],'method':'replay ORIGINAL FULL stored token sequence; no prompt+detached-tail splice; all generated span rank when <=1024 on 0.6B'}
 def replay(ids,n,cid):
  rec={'id':cid,'token_ids':ids,'prompt_tokens':n,'spans':{'generated':list(range(n,len(ids)))}}
  return analyze(model,rec)
 for split in ['fit','transfer']:
  for j,t in enumerate(tw[split]):
   res=replay(t['ids'],len(t['common_ids']),f'twin_{split}_{j}')
   out['twins'].append({'split':split,'kind':t['kind'],'gold':t['gold'],'summary':res['span_summaries']['generated']})
 originals={x['id']:x for x in r['original']};edits={x['id']:x for x in r['edited']};tasks={x['id']:x for x in r['tasks']}
 deltas={}
 for l in [19,21]:
  full=torch.load(old.WS360_DIR/f'edit_layer_{l}.pt',weights_only=True,map_location='cpu')['delta']
  cols=(full!=0).any(0).nonzero().flatten();assert len(cols)==64
  deltas[l]=(cols.cuda(),full[:,cols].cuda());del full
 golden={x['layer']:x['edited_sha256']for x in r['manifest']['layers']}
 for q in r['paired']['edited']['cut_to_closed_correct']:
  task=tasks[q];prompt=tok.apply_chat_template([{'role':'user','content':task['q']}],tokenize=False,add_generation_prompt=True,enable_thinking=True);ids=tok.encode(prompt,add_special_tokens=False);n=len(ids)
  baseline=replay(ids+originals[q]['generated_ids'],n,q+'_original_full')
  originals_w={l:model.model.layers[l].mlp.down_proj.weight[:,cols].detach().clone()for l,(cols,d)in deltas.items()}
  try:
   for l,(cols,d)in deltas.items():
    w=model.model.layers[l].mlp.down_proj.weight;w[:,cols]=(originals_w[l].float()-r['manifest']['alpha']*d).to(torch.bfloat16)
    digest=hashlib.sha256(w.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    assert digest==golden[l],('edit hash mismatch',l,digest,golden[l])
   edited=replay(ids+edits[q]['generated_ids'],n,q+'_edited_full')
  finally:
   for l,orig in originals_w.items():
    w=model.model.layers[l].mlp.down_proj.weight;cols=deltas[l][0];w[:,cols]=orig;assert torch.equal(w[:,cols],orig)
  out['rescued_heldout'].append({'id':q,'original':baseline,'edited':edited,'edited_weight_hashes_matched':True,'original_repeat4':originals[q]['repeat4'],'edited_repeat4':edits[q]['repeat4']})
  save(ROOT/'checkpoints'/'Qwen3-0.6B'/'ws360.json',out)
 return out

def compact_rec(r):
 # Source JSON contains large old lens/router arrays; retain only replay inputs/metadata.
 keys=('id','token_ids','tokens','prompt_tokens','spans','prompt','exp','family','format','group','pair','kind','stage','generated_text','ended_with_eos','hit_limit','prefill_next','generation_predictive_entropy_nats','replay_next_entropy_nats')
 return {k:r[k] for k in keys if k in r}

def records(name):
 if '35B'in name:
  dirs=[('bp',old.BASEPOST_DIR/'raw'/name)]
 else:dirs=[('raw',old.INTERP_DIR/'raw'/name),('p160',old.INTERP_DIR/'priming160_raw'/name),('s160',old.INTERP_DIR/'saddle160_raw'/name)]
 rows=[]
 for tag,d in dirs:
  for p in sorted(d.glob('*.json')):
   r=json.loads(p.read_text())
   if 'token_ids'in r and r.get('id')and r.get('family') not in ('smoke','e1'):rows.append((tag+':'+r['id'],compact_rec(r),p))
 if name=='Qwen3.5-35B-A3B':
  # Exact same complete sequences as Base, including first five generated tokens.
  for p in sorted((old.BASEPOST_DIR/'raw'/'Qwen3.5-35B-A3B-Base').glob('bp_chat_*.json')):
   r=json.loads(p.read_text())
   if r.get('group') in ('bare','natural_syzygy','syzygy'):
    rows.append(('common_base:'+r['id'],compact_rec(r),p))
 return rows

def run(stage,anchors_only=False):
 name=STAGES[stage];assert torch.cuda.is_available()and 'GB10'in torch.cuda.get_device_name(), 'Spark only'
 drop();assert avail()>105, f'pre-load MemAvailable {avail():.2f} <=105 GiB'
 threading.Thread(target=watchdog,daemon=True).start();t0=time.time()
 log('LOAD',name,'MemAvailable',avail())
 if '35B'in name:tok,model,plan=old.bp_loader.load(name)
 else:tok,model=old.core.load_model(name);plan={}
 guard('loaded');model.eval()
 if anchors_only:
  p=ROOT/f'manifold_{name}.json';d=json.loads(p.read_text());d['exp4_tangent_projection']=exp4(tok,model,name,only_stutter=True);d['anchor_supplement_resources']=PEAK;d['geometry_notes']='unit-sphere operational geometry; angles radians unless deg; erank entropy exp; full generated span rank; no centered metrics; long non-generated prompt spans use last256';save(p,d);return
 rows=records(name);out={};checkpoint=ROOT/'checkpoints'/name;checkpoint.mkdir(parents=True,exist_ok=True)
 for j,(cid,rec,path)in enumerate(rows):
  dest=checkpoint/(hashlib.sha256(cid.encode()).hexdigest()+'.json')
  if dest.exists():
   res=json.loads(dest.read_text());assert res['token_sha256']==hashlib.sha256(json.dumps(rec['token_ids']).encode()).hexdigest(),f'stale token checkpoint: {cid}'
  else:
   log(name,j+1,len(rows),cid,'T',len(rec['token_ids']),'available',round(avail(),2));res=analyze(model,rec);res['source_file']=str(path);save(dest,res)
  out[cid]=res
  if j%5==0:drop()
 ex=None;ws=None
 if name in ('Qwen3-0.6B','Qwen3.8-27B-FP8'):ex=exp4(tok,model,name)
 if name=='Qwen3-0.6B':ws=ws360(tok,model)
 save(ROOT/f'manifold_{name}.json',{'model':name,'streaming_version':2,'num_layers':len(model.model.layers),'hidden_size':model.config.hidden_size,'records':out,'exp4_tangent_projection':ex,'ws360_repetition_bubble_probe':ws,'load_plan':plan,'resources':PEAK,'elapsed_seconds':time.time()-t0,'geometry_notes':'unit-sphere operational geometry; angles radians unless deg; erank entropy exp; full generated span <=512 (0.6B <=1024); no centered metrics; long non-generated prompt spans use last256; actual assistant marker and think scaffold separate'})
 log('MODEL COMPLETE',name,PEAK)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--anchors-only',action='store_true');ap.add_argument('--stage',required=True,choices=list(STAGES)+['analyze','selftest']);args=ap.parse_args()
 if args.stage=='selftest':save(ROOT/'self_test.json',old.self_test_geometry())
 elif args.stage=='analyze':subprocess.run([sys.executable,str(ROOT/'analyze_paper100.py')],check=True)
 else:run(args.stage,args.anchors_only)
if __name__=='__main__':main()
