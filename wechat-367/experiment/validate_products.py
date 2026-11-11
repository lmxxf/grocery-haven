#!/usr/bin/env python3
"""CPU-only, streaming layer validation. Never initializes CUDA."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='4';os.environ['OMP_NUM_THREADS']='4'
import json,hashlib,time,argparse
from pathlib import Path
import numpy as np
from safetensors.numpy import load_file
R=Path(__file__).resolve().parent
D=5120

def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def atomic(p,x):
 q=p.with_suffix('.tmp');q.write_text(json.dumps(x,ensure_ascii=False,allow_nan=False,indent=2));q.replace(p)
def validate(l):
 p=R/f'L{l:02d}';checks={};files={}
 for n in ['complete.json','statistics.json','contexts.json','vocabulary_readouts.json','oriented.safetensors','saelens_adapter.safetensors','native/icalens.json',f'native/artifacts/resid_post/layer_{l:02d}.safetensors','probes.npy']:
  f=p/n;assert f.exists(),str(f);files[n]={'bytes':f.stat().st_size,'sha256':sha(f)}
 comp=read(p/'complete.json');s=read(p/'statistics.json');meta=read(p/'native/icalens.json');ft=meta['layers'][str(l)]['fitting']
 assert comp['layer']==s['layer']==l and comp['finite']
 assert meta['hidden_size']==D and meta['input_preprocessing']['row_normalization']=='l2'
 assert ft['n_iter']==ft['max_iter']==50 and ft['n_samples']==200704 and ft['fun']=='logcosh' and ft['ica_algorithm']=='parallel'
 checks['configuration']=True
 for sp in ['fit','heldout']:
  for k in ['skewness','excess_kurtosis']:
   v=np.asarray(s['stats'][sp][k]);assert v.shape==(D,)and np.isfinite(v).all(),(l,sp,k)
  k=np.asarray(s['stats'][sp]['excess_kurtosis']);assert int((k>1).sum())==s['stats'][sp]['kappa_gt1'];assert int((k>10).sum())==s['stats'][sp]['kappa_gt10']
 assert comp['kappa_held_gt1']==s['stats']['heldout']['kappa_gt1']and comp['kappa_held_gt10']==s['stats']['heldout']['kappa_gt10']
 for field in ['language_delta_fit','language_delta_heldout']:
  v=np.asarray(s[field]);assert v.shape==(D,)and np.isfinite(v).all()
 assert np.asarray(s['probe_scores']).shape==(142,D)and np.isfinite(s['probe_scores']).all()
 idx=np.asarray(s['top_heldout']['indices']);assert idx.shape==(5,D)and idx.min()>=0 and idx.max()<51200
 for n in ['oriented.safetensors','saelens_adapter.safetensors',f'native/artifacts/resid_post/layer_{l:02d}.safetensors']:
  tensors=load_file(str(p/n));assert all(np.isfinite(v).all()for v in tensors.values()),(l,n)
 checks['all_stored_tensors_finite']=True
 t=load_file(str(p/'oriented.safetensors'));raw=load_file(str(p/f'native/artifacts/resid_post/layer_{l:02d}.safetensors'))
 C=t['components'];M=t['mixing'];c=t['center'];sign=t['orientation_sign'];assert C.shape==M.shape==(D,D)and c.shape==sign.shape==(D,)
 assert set(np.unique(sign)).issubset({-1.,1.})
 assert np.array_equal(C,raw['reading_matrix']*sign[:,None])and np.array_equal(M,raw['writing_matrix']*sign[None,:])and np.array_equal(c,raw['center'])
 ids=np.linspace(0,D-1,32,dtype=int);duality=C[ids]@M;duality[np.arange(len(ids)),ids]-=1
 checks['sampled_reading_writing_duality_maxabs']=float(np.abs(duality).max())
 assert checks['sampled_reading_writing_duality_maxabs']<.05,(l,checks)
 x=np.load(p/'probes.npy');xn=x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12);expected=(xn-c)@C.T;actual=np.asarray(s['probe_scores'],dtype=np.float32)
 checks['probe_scores_recompute_relative_l2']=float(np.linalg.norm(expected-actual)/max(np.linalg.norm(expected),1e-12))
 checks['probe_scores_recompute_maxabs']=float(np.max(np.abs(expected-actual)))
 assert checks['probe_scores_recompute_relative_l2']<.01,(l,checks)
 adapter=load_file(str(p/'saelens_adapter.safetensors'));norm=np.maximum(np.linalg.norm(M,axis=0),1e-12)
 assert np.allclose(adapter['W_enc'],C.T*norm[None,:],rtol=1e-5,atol=1e-5)
 assert np.allclose(np.linalg.norm(adapter['W_dec'],axis=1),1,rtol=1e-4,atol=1e-4)
 vocab=read(p/'vocabulary_readouts.json')['axes'];assert set(vocab)==set(map(str,s['selected_candidate_axes']))
 for ax in vocab.values():
  for mode in ['vanilla','jlens_n100']:
   assert len(ax[mode])==20 and all(np.isfinite(v['logit'])for v in ax[mode])
 if l==63:assert all(v['vanilla']==v['jlens_n100']for v in vocab.values())
 if l in [0,16,38,41,56,63]:
  gen=read(p/'steering.json');assert len(gen['runs'])==8;files['steering.json']={'bytes':(p/'steering.json').stat().st_size,'sha256':sha(p/'steering.json')}
 checks['PASS']=True
 return {'layer':l,'checks':checks,'files':files,'time':time.time()}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args();p=R/'validation.json';old=read(p)if p.exists()else{};by={int(v['layer']):v for v in old.get('layers',[])}
 for l in range(64):
  if l in by:continue
  if a.partial and not(R/f'L{l:02d}'/'vocabulary_readouts.json').exists():continue
  try:v=validate(l)
  except Exception as e:
   if a.partial:print('WAIT_OR_ERROR',l,repr(e),flush=True);continue
   raise
  by[l]=v;atomic(p,{'complete':len(by)==64,'layers':[by[k]for k in sorted(by)],'validation_scope':'all weights finite, SHA256, config and threshold counts; sampled duality32rows and full142 probe score reconstruction; CPU only'});print('VALIDATED',l,v['checks'],flush=True)
 assert a.partial or len(by)==64
