#!/usr/bin/env python3
"""Geometry equivalence and resource contract checks; no large model load."""
import json,sys,math,hashlib
from pathlib import Path
import numpy as np
import torch
import run_paper100_manifold_awakening as new
R=Path(__file__).resolve().parent
report={}
torch.manual_seed(100)
h=torch.randn(145,64,device='cuda');expected,_=new.old.compute_all_manifold_metrics(h[None,None].expand(2,1,-1,-1))
collected={}
for t in range(0,len(h),64):
 lo=max(0,t-16);hi=min(len(h),t+64)
 for k,v in new.temporal(h[lo:hi]).items():collected.setdefault(k,np.full(len(h),np.nan))[t:hi]=v[t-lo:hi-lo]
errors={k:float(np.nanmax(np.abs(v-expected[k][0])))for k,v in collected.items()}
assert max(errors.values())<1e-4,errors
report['tiled_equivalence_max_abs_error']=errors
report['analytical_geometry']=new.old.self_test_geometry()
for p in R.glob('manifold_*.json'):
 d=json.loads(p.read_text())
 if d.get('streaming_version')!=2:continue
 assert d['resources']['minimum_available_GiB']>=22
 expected={cid:hashlib.sha256(json.dumps(r['token_ids']).encode()).hexdigest()for cid,r,src in new.records(d['model'])}
 assert set(expected)==set(d['records']),(d['model'],'missing/extra replay records',set(expected)-set(d['records']))
 assert all(expected[cid]==r['token_sha256']for cid,r in d['records'].items()),'source token hash mismatch'

 for r in d['records'].values():
  for k,v in r.get('token_curves',{}).items():
   if k.endswith('_mid'):assert len(v)==r['total_tokens'],(r['id'],k,'curve length')
  for s in r['span_summaries'].values():
   for band in ['mid','early','deep','all']:
    m=s.get(band,{})
    for key,upper in [('erank_dir',5),('erank_layer',5),('erank_dir_16',16)]:
     v=m.get(key)
     assert v is None or .99<=v<=upper+.01,(p,r['id'],key,v)
    v=m.get('s_geo');assert v is None or 0<=v<=math.pi
 if d.get('exp4_tangent_projection'):assert len(d['exp4_tangent_projection']['pairs'])==6
 report[p.name]={'records':len(d['records']),'resource_floor_pass':True,'geometry_bounds_pass':True,'source_coverage_and_token_hashes_pass':True,'curve_lengths_pass':True}
(R/'streaming_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
