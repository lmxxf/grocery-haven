#!/usr/bin/env python3
import os,time,json,argparse,threading,gc,sys,mmap
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'icalens_pkg'))
def avail():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))/1048576
def guard():
 while True:
  if avail()<22:os._exit(73)
  time.sleep(.25)
threading.Thread(target=guard,daemon=True).start()
import numpy as np
import torch
from safetensors.torch import save_file
from icalens import ICALens
D=5120;torch.set_num_threads(8);torch.set_float32_matmul_precision('high')
def save(p,x):
 p=Path(p);q=p.with_suffix('.tmp');q.write_text(json.dumps(x,ensure_ascii=False,allow_nan=False,indent=2));q.replace(p)
def extract(layers):
 from loader_reference import load_model
 rows=[json.loads(x) for x in (R/'corpus.jsonl').read_text().splitlines()];counts={s:sum(len(r['token_ids']) for r in rows if r['split']==s)for s in ['fit','heldout']}
 need=sum(counts.values())*D*4*len(layers)
 import shutil
 assert shutil.disk_usage(R).free>need+10*2**30
 arrays={}
 for l in layers:
  p=R/f'L{l:02d}';p.mkdir(exist_ok=True)
  for s,n in counts.items():arrays[l,s]=np.lib.format.open_memmap(p/f'{s}.npy',mode='w+',dtype='float32',shape=(n,D))
 tok,model=load_model('Qwen3.8-27B-FP8');current={};hooks=[]
 for l in layers:
  def hook(m,i,o,l=l):current[l]=(o[0]if isinstance(o,tuple)else o).detach().float().cpu().numpy()[0]
  hooks.append(model.model.layers[l].register_forward_hook(hook))
 pos={s:0 for s in counts}
 with torch.inference_mode():
  for i,r in enumerate(rows):
   ids=torch.tensor([r['token_ids']],device='cuda');model.model(input_ids=ids,use_cache=False);s=r['split'];n=ids.shape[1]
   for l in layers:
    a=arrays[l,s];assert np.isfinite(current[l]).all();a[pos[s]:pos[s]+n]=current[l];a.flush();a._mmap.madvise(mmap.MADV_DONTNEED)
   pos[s]+=n;current.clear()
   if i%10==0:print('EXTRACT',i,len(rows),pos,'available_GiB',avail(),flush=True)
  probes=json.loads((R/'probes.json').read_text());pa={l:[]for l in layers}
  for r in probes:
   text=r['text'].rstrip('.。') if r['group']=='parallel' else r['text'];ids=tok.encode(text,add_special_tokens=False)
   if r['group']=='parallel':ids+=tok.encode('\n',add_special_tokens=False)
   model.model(input_ids=torch.tensor([ids],device='cuda'),use_cache=False)
   for l in layers:pa[l].append(current[l][-1].copy())
   current.clear()
 for l in layers:
  np.save(R/f'L{l:02d}'/'probes.npy',np.stack(pa[l]));save(R/f'L{l:02d}'/'extracted.json',{'layer':l,'counts':counts,'finite':True,'probe_policy':'parallel same newline suffix; polysemy target last token','time':time.time()})
 print('EXTRACTION_COMPLETE',layers,flush=True)
def scores(a,C,c):
 for start in range(0,len(a),4096):
  x=torch.tensor(np.array(a[start:start+4096]),device='cuda');x=x/x.norm(dim=1,keepdim=True).clamp_min(1e-12);yield start,(x-c)@C.T

def fit(l):
 p=R/f'L{l:02d}';a=np.load(p/'fit.npy',mmap_mode='r');lens=ICALens(model_id='Qwen/Qwen3.8-27B-FP8',model_type='instruct',activation_site='resid_post',layer_indexing='block_output_zero_based',row_normalize=True)
 if (p/'native'/'icalens.json').exists():lens=ICALens.from_pretrained(p/'native')
 else:
  values=torch.tensor(np.array(a),device='cuda')
  lens.fit(values,layer=l,n_components=D,algorithm='parallel',fun='logcosh',max_iter=50,random_state=367,progress=True,device='cuda',batch_size=8192,objective_every=5,provenance={'corpus_sha256':json.loads((R/'corpus_manifest.json').read_text())['sha256'],'precision':'float32, matmul high; FP64 covariance accumulator','tokens':len(a)})
  lens.save(p/'native');del values;gc.collect();torch.cuda.empty_cache()
 z=lens._get_layer(l);C=torch.tensor(z.reading_matrix,device='cuda');c=torch.tensor(z.center,device='cuda');M=torch.tensor(z.writing_matrix,device='cuda')
 stats={};sign=None;tops=None
 for split in ['fit','heldout']:
  data=np.load(p/f'{split}.npy',mmap_mode='r');sums=torch.zeros((4,D),dtype=torch.float64,device='cuda');topv=torch.full((5,D),-float('inf'),device='cuda');topi=torch.zeros((5,D),dtype=torch.long,device='cuda')
  for start,y in scores(data,C,c):
   if split=='heldout':y=y*sign
   yd=y.double()
   for k in range(4):sums[k]+=yd.pow(k+1).sum(0)
   if split=='heldout':
    v,ii=y.topk(5,dim=0);v2=torch.cat([topv,v]);i2=torch.cat([topi,ii+start]);topv,idx=v2.topk(5,dim=0);topi=i2.gather(0,idx)
  m1,m2,m3,m4=sums/len(data);v=(m2-m1*m1).clamp_min(1e-20);sk=(m3-3*m1*m2+2*m1**3)/v**1.5;ku=(m4-4*m1*m3+6*m1*m1*m2-3*m1**4)/v**2-3
  if sign is None:sign=torch.where(sk>=0,1.,-1.);sk=sk*sign
  stats[split]={'skewness':sk.cpu().tolist(),'excess_kurtosis':ku.cpu().tolist(),'kappa_gt1':int((ku>1).sum()),'kappa_gt10':int((ku>10).sum())}
  if split=='heldout':tops={'values':topv.cpu().tolist(),'indices':topi.cpu().tolist()}
 Co=C*sign[:,None];Mo=M*sign[None,:];pn=np.load(p/'probes.npy');x=torch.tensor(pn,device='cuda');y=((x/x.norm(dim=1,keepdim=True))-c)@Co.T;probes=json.loads((R/'probes.json').read_text());diff={}
 for split in ['fit','heldout']:
  pairs={}
  for i,r in enumerate(probes):
   if r['group']=='parallel'and r['split']==split:pairs.setdefault(r['pair'],{})[r['lang']]=i
  diff[split]=torch.stack([y[v['zh']]-y[v['en']]for v in pairs.values()]).mean(0)
 axis=int(diff['fit'].abs().argmax());selected=torch.tensor(sorted(set(torch.tensor(stats['heldout']['excess_kurtosis']).topk(96).indices.tolist()+diff['fit'].abs().topk(8).indices.tolist())),device='cuda')
 save_file({'components':Co.cpu().contiguous(),'mixing':Mo.cpu().contiguous(),'center':c.cpu().contiguous(),'orientation_sign':sign.cpu()},str(p/'oriented.safetensors'))
 norms=Mo.norm(dim=0).clamp_min(1e-12);enc=Co.T*norms[None,:];save_file({'W_enc':enc.cpu().contiguous(),'W_dec':(Mo.T/norms[:,None]).cpu().contiguous(),'b_enc':(-c@enc).cpu(),'b_dec':c.cpu()},str(p/'saelens_adapter.safetensors'))
 save(p/'saelens_adapter.json',{'d_in':D,'d_sae':D,'activation_fn_str':'relu','normalize_activations':'none','apply_b_dec_to_input':False,'required_external_preprocessing':'row L2 normalization; positive half-wave adapter is not signed ICA reconstruction','unit_decoder':True})
 save(p/'statistics.json',{'layer':l,'stats':stats,'language_axis':axis,'language_delta_fit':diff['fit'].cpu().tolist(),'language_delta_heldout':diff['heldout'].cpu().tolist(),'selected_candidate_axes':selected.cpu().tolist(),'probe_scores':y.cpu().tolist(),'top_heldout':tops,'component_ids':'official contrast ranking retained; orientation based on fit skewness only'})
 # Causal left contexts for every selected candidate.
 rows=[json.loads(s)for s in (R/'corpus.jsonl').read_text().splitlines() if json.loads(s)['split']=='heldout'];ends=np.cumsum([len(r['token_ids'])for r in rows]);contexts={}
 for j in selected.cpu().tolist():
  contexts[j]=[]
  for rank in range(5):
   ix=tops['indices'][rank][j];ri=int(np.searchsorted(ends,ix,side='right'));off=ix-(int(ends[ri-1])if ri else 0);r=rows[ri];contexts[j].append({'activation':tops['values'][rank][j],'lang':r['lang'],'left_context':''.join(r['tokens'][max(0,off-64):off+1]),'document_id':r['document_id']})
 save(p/'contexts.json',contexts)
 save(p/'complete.json',{'layer':l,'time':time.time(),'finite':all(np.isfinite(t.cpu().numpy()).all()for t in [Co,Mo,c]),'kappa_held_gt1':stats['heldout']['kappa_gt1'],'kappa_held_gt10':stats['heldout']['kappa_gt10'],'language_axis':axis,'note':'candidate axes are not automatically verified concepts'})
 print('LAYER_COMPLETE',l,flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['extract','fit']);ap.add_argument('layers',nargs='+',type=int);args=ap.parse_args()
 if args.mode=='extract':extract(args.layers)
 else:
  for l in args.layers:fit(l)
