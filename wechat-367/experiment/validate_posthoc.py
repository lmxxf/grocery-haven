import os
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OPENBLAS_NUM_THREADS']='4'
import json,hashlib,time
from pathlib import Path
import numpy as np
from safetensors.numpy import load_file
R=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def save(p,x):
 q=p.with_suffix('.tmp');q.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False));q.replace(p)
source=json.loads((R/'source_sha256.json').read_text());records=[]
for relative,info in source['files'].items():
 p=R/relative;assert p.stat().st_size==info['bytes']and sha(p)==info['sha256'],relative
slave=json.loads((R/'source_sha256_slave.json').read_text());assert len(slave['layers'])==32
for relative,info in slave['files'].items():assert source['files'][relative]==info,relative
print('SLAVE_TO_MAIN_SHA256_MATCH',len(slave['files']),flush=True)
print('SOURCE_TO_LOCAL_SHA256_MATCH',len(source['files']),flush=True)
probe=json.loads((R/'polysemy_probes.json').read_text());cap=json.loads((R/'polysemy_capture.json').read_text());assert sha(R/'polysemy_probes.json')==cap['probes_sha256'];tokens={x['id']:x for x in cap['tokens']};token_ids={}
for r in probe:token_ids.setdefault(r['target'],set()).add(tokens[r['id']]['token_ids'][-1])
assert all(len(v)==1 for v in token_ids.values()),token_ids
for l in range(64):
 p=R/f'L{l:02d}';statistics=json.loads((p/'statistics.json').read_text())
 for split,N in [('fit',200704),('heldout',51200)]:
  k=np.asarray(statistics['stats'][split]['excess_kurtosis']);assert k.min()>=-2.0001 and k.max()<=N-5+1/(N-1)+.1,(l,split,float(k.min()),float(k.max()))
 t=load_file(str(p/'oriented.safetensors'));x=np.load(p/'polysemy_probes.npy');assert x.shape==(72,5120)and np.isfinite(x).all();a=json.loads((p/'polysemy_analysis.json').read_text());actual=np.asarray(a['probe_scores'],np.float32);y=(x/np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-12)-t['center'])@t['components'].T;err=float(np.linalg.norm(y-actual)/max(np.linalg.norm(y),1e-12));assert err<.001,(l,err)
 for name,d in a['sense_contrasts'].items():
  for v in d['top5_fit_axes']:
   assert v['heldout_total']==8 and sum(x['correct']for x in v['heldout_cases'])==v['heldout_correct']
 vocab=json.loads((p/'polysemy_readouts.json').read_text());assert set(vocab['axes'])==set(map(str,a['extra_axes']))
 for v in vocab['axes'].values():
  for sign in ['positive','negative']:
   for mode in ['vanilla','jlens_n100']:assert len(v[sign][mode])==20 and all(np.isfinite(t['logit'])for t in v[sign][mode])
 if l==63:assert all(v[s]['vanilla']==v[s]['jlens_n100']for v in vocab['axes'].values()for s in ['positive','negative'])
 context=json.loads((p/'contexts_decoded.json').read_text());assert set(map(str,a['extra_axes'])).issubset(context['axes'])
 records.append({'layer':l,'finite':True,'polysemy_score_recompute_relative_l2':err,'heldout_decisions_recounted':True,'population_kurtosis_bounds_valid':True});print('POSTHOC_VALIDATED',l,err,flush=True)
save(R/'posthoc_validation.json',{'complete':len(records)==64,'source_to_local_sha256_match':True,'slave_to_main_sha256_match':True,'slave_files_compared':len(slave['files']),'files_compared':len(source['files']),'target_last_token_ids':{k:list(v)for k,v in token_ids.items()},'layers':records,'time':time.time()})
