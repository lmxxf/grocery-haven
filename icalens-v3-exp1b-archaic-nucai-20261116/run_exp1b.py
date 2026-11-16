#!/usr/bin/env python3
import os,sys,time,json,traceback,importlib.util,gc
from pathlib import Path
R=Path(__file__).resolve().parent
V3=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3');HEAVY=V3/'experiments/exp1b_archaic_nucai'
os.environ['TRITON_CACHE_DIR']=str(V3/'triton_cache');os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,str(V3));sys.path.insert(0,str(R))
def save(name,x):(R/name).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def main():
 import torch,numpy as np
 from model_loader import load_model
 torch.set_num_threads(8);torch.set_float32_matmul_precision('highest')
 probes=json.loads((R/'probes.json').read_text());n=len(probes);start=time.time();tok,model=load_model()
 last=np.lib.format.open_memmap(HEAVY/'activations_last.npy',mode='w+',dtype='float32',shape=(64,n,5120));mean=np.lib.format.open_memmap(HEAVY/'activations_mean.npy',mode='w+',dtype='float32',shape=(64,n,5120));cur=[0,0];handles=[]
 for l,block in enumerate(model.model.layers):
  def hook(m,i,o,l=l):
   h=(o[0] if isinstance(o,tuple) else o)[0];j,k=cur;last[l,j]=h[-1].float().cpu().numpy();mean[l,j]=h[k:].float().mean(0).cpu().numpy()
  handles.append(block.register_forward_hook(hook))
 total_tokens=0
 with torch.inference_mode():
  for j,p in enumerate(probes):
   cur[:]=[j,p['target_start']];model.model(input_ids=torch.tensor([p['input_ids']],device='cuda'),use_cache=False);total_tokens+=len(p['input_ids'])
   if j%5==0 or j==n-1:
    status=dict(stage='forward',done=j+1,total=n,forward_tokens=total_tokens,seconds=time.time()-start);save('progress.json',status);print('FORWARD',status,flush=True)
 for h in handles:h.remove()
 last.flush();mean.flush();save('forward_complete.json',dict(probes=n,tokens=total_tokens,seconds=time.time()-start,full_model_loads=1))
 # Retain the single loaded model if report code needs a repair; no repeated 27B load.
 while True:
  while not (R/'analysis.ready').exists():time.sleep(2)
  try:
   spec=importlib.util.spec_from_file_location('exp1b_analysis',R/'analysis_exp1b.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.run(model,tok);break
  except Exception:
   (R/'analysis.ready').unlink(missing_ok=True);err=traceback.format_exc();(R/'analysis_error.log').write_text(err);print(err,flush=True);save('progress.json',dict(stage='analysis_needs_repair',model_resident=True));gc.collect();torch.cuda.empty_cache()
 print('COMPLETE',time.time()-start,flush=True)
if __name__=='__main__':main()
