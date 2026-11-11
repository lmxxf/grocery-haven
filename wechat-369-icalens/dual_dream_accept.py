#!/usr/bin/env python3
"""Cross-check saved coordinates, indexing, signs and source fingerprints without a model."""
import hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'dual_dream'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 m=json.loads((OUT/'analysis_manifest.json').read_text());assert m['status']=='PASS'and m['layers']==list(range(64))
 a=np.load(OUT/'analysis_coordinates.npz');keys=a['keys'].tolist();ys=a['coordinates'];assert ys.shape==(64,20,5120)and np.isfinite(ys).all()
 fingerprints=[];positions=0;differences=0
 for layer in range(64):
  d=json.loads((OUT/f'analysis_layers/layer_{layer:02d}.json').read_text());assert d['layer']==layer and set(d['entries'])==set(keys)
  fingerprints.append(d['input_fingerprint'])
  for i,key in enumerate(keys):
   y=ys[layer,i];e=d['entries'][key];expected=np.argsort(-np.abs(y),kind='stable')[:10].tolist();assert [x['axis']for x in e['top10_axes']]==expected
   sq=y.astype(np.float64)**2;p=sq/sq.sum();met=e['metrics'];assert np.isclose(met['participation_ratio'],1/(p*p).sum())
   assert np.isclose(met['top10_square_share'],np.sort(p)[-10:].sum())
   for axis in e['top10_axes']:
    j=axis['axis'];assert np.isclose(axis['y'],y[j])
    if axis['readout_key']:assert axis['readout_key']==f'{j}:{1 if y[j]>=0 else -1:+d}'
   positions+=1
  for cmp in d['differences'].values():
   delta=ys[layer,keys.index(cmp['left'])]-ys[layer,keys.index(cmp['right'])]
   for side,sign in [('positive',1),('negative',-1)]:
    chosen=cmp[side];assert [x['axis']for x in chosen]==np.argsort(-sign*delta,kind='stable')[:8].tolist()
    for x in chosen:
     j=x['axis'];assert np.isclose(x['delta_y'],delta[j])
     if x['readout_key']:assert x['readout_key']==f'{j}:{1 if delta[j]>=0 else -1:+d}'
   differences+=1
  for rd in d['direction_readouts'].values():
   for mode,n in [('jlens',8),('vanilla',5)]:
    t=rd[mode]['top_tokens'];assert len(t)==n and len({x['token_id']for x in t})==n
    assert all(t[j]['logit']>=t[j+1]['logit']for j in range(n-1))
 assert all(x==fingerprints[0]for x in fingerprints)
 expected={'capture_json_sha256':OUT/'capture.json','residual_npz_sha256':OUT/'capture_residuals.npz','analysis_script_sha256':ROOT/'dual_dream_analyze.py','ica_manifest_sha256':ROOT/'hf_release/icalens.json','j_lens_checkpoint_sha256':ROOT/'lens_n100.pt'}
 assert all(fingerprints[0][k]==sha(p)for k,p in expected.items())
 b=json.loads((OUT/'analysis_brief.json').read_text());assert len(b['L63_actual_prefill_comparisons'])==9
 assert all(x['top1_match']and x['top10_intersection']==10 for x in b['L63_actual_prefill_comparisons'])
 result=dict(status='PASS',layers=64,position_layer_checks=positions,difference_layer_checks=differences,coordinate_shape=list(ys.shape),uniform_current_source_fingerprints=True,L63_actual_model_primary_positions=9,maximum_reconstruction_error=b['maximum_reconstruction_error'])
 (OUT/'experiment_acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
