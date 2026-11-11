#!/usr/bin/env python3
"""CPU-only component scoring and heldout sense contrasts. No model fitting."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OPENBLAS_NUM_THREADS']='4';os.environ['OMP_NUM_THREADS']='4'
import json,time
from pathlib import Path
import numpy as np
from safetensors.numpy import load_file
R=Path(__file__).resolve().parent
pairs=[('bank','bank_finance','bank_river'),('apple_en','apple_fruit','apple_company'),('苹果_zh','苹果水果','苹果公司')]
def save(p,x):
 q=p.with_suffix('.tmp');q.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False));q.replace(p)
def main():
 probes=json.loads((R/'polysemy_probes.json').read_text());all_layers=[]
 for l in range(64):
  p=R/f'L{l:02d}';t=load_file(str(p/'oriented.safetensors'));x=np.load(p/'polysemy_probes.npy');xn=x/np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-12);y=(xn-t['center'])@t['components'].T;assert np.isfinite(y).all()
  stats=json.loads((p/'statistics.json').read_text());results={};contrasts={};extra=set()
  for name,A,B in pairs:
   ids={}
   for label in [A,B]:
    for split in ['fit','heldout']:ids[label,split]=[i for i,r in enumerate(probes)if r['label']==label and r['split']==split]
   ma=y[ids[A,'fit']].mean(0);mb=y[ids[B,'fit']].mean(0);delta=ma-mb;contrasts[name]=delta;axes=np.argsort(-np.abs(delta))[:5];recs=[]
   for axis in axes:
    axis=int(axis);extra.add(axis);sgn=float(np.sign(delta[axis])or 1);threshold=float((ma[axis]+mb[axis])/2);actual=[];correct=0
    for label in [A,B]:
     for i in ids[label,'heldout']:
      pred=A if sgn*(y[i,axis]-threshold)>0 else B;ok=pred==label;correct+=ok;actual.append({'id':probes[i]['id'],'label':label,'score':float(y[i,axis]),'prediction':pred,'correct':bool(ok)})
    hold_delta=float(y[ids[A,'heldout'],axis].mean()-y[ids[B,'heldout'],axis].mean())
    recs.append({'axis':axis,'fit_delta_A_minus_B':float(delta[axis]),'heldout_delta_A_minus_B':hold_delta,'same_sign':bool(delta[axis]*hold_delta>0),'threshold':threshold,'A_direction_sign':sgn,'heldout_correct':correct,'heldout_total':8,'heldout_accuracy':correct/8,'heldout_cases':actual,'natural_heldout_kurtosis':stats['stats']['heldout']['excess_kurtosis'][axis]})
   results[name]={'positive_label':A,'negative_label':B,'n_fit_per_sense':8,'n_heldout_per_sense':4,'top5_fit_axes':recs}
  en=contrasts['apple_en'];zh=contrasts['苹果_zh'];cos=float(en@zh/(np.linalg.norm(en)*np.linalg.norm(zh)));enaxis=results['apple_en']['top5_fit_axes'][0]['axis'];za=[i for i,r in enumerate(probes)if r['label']=='苹果水果'];zb=[i for i,r in enumerate(probes)if r['label']=='苹果公司'];transfer=float(y[[i for i in za if probes[i]['split']=='heldout'],enaxis].mean()-y[[i for i in zb if probes[i]['split']=='heldout'],enaxis].mean())
  product={'layer':l,'sense_contrasts':results,'apple_cross_language_contrast_cosine':cos,'english_selected_axis_chinese_heldout_delta':transfer,'extra_axes':sorted(extra),'probe_scores':y.tolist(),'limitations':'synthetic small heldout; axis selection uses fit only, no claim of clean concept or causal sense disentanglement'}
  save(p/'polysemy_analysis.json',product);all_layers.append({k:v for k,v in product.items()if k!='probe_scores'});print('POLYSEMY_ANALYZED',l,flush=True)
 save(R/'polysemy_summary.json',{'time':time.time(),'probes':probes,'protocol':'12 contexts/sense; 8 axis-selection/calibration, 4 heldout; exact same terminal spelling per language; component labels not aligned across layers','layers':all_layers})
if __name__=='__main__':main()
