"""Memory-bounded storage adaptation of the unmodified official estimator.
No low-rank approximation; matrices are exact full-width FP32 accumulators.
Source: anthropics/jacobian-lens jlens/fitting.py, Apache-2.0.
"""
import inspect,mmap,tempfile,os,gc,json,time,shutil,threading
from pathlib import Path
import numpy as np
import torch
from jlens.fitting import jacobian_for_prompt as official
from jlens import JacobianLens

class DiskJacobians:
 def __init__(self,root):self.root=Path(root);self.maps=[]
 def zeros(self,d1,d2,**kw):
  path=self.root/f'layer-{len(self.maps)}.bin'
  with open(path,'wb') as f:f.truncate(d1*d2*4)
  a=np.memmap(path,dtype='float32',mode='r+',shape=(d1,d2));self.maps.append(a)
  return torch.from_numpy(a)
 def release(self):
  for a in self.maps:a.flush();a._mmap.madvise(mmap.MADV_DONTNEED)
 def function(self):
  src=inspect.getsource(official)
  old='torch.zeros(d_model, d_model, dtype=torch.float32)'
  assert old in src
  src=src.replace(old,'disk_zeros(d_model, d_model)')
  src=src.replace('            del grads','            del grads\n            if pass_idx % 10 == 0: disk_release()')
  env=dict(official.__globals__,disk_zeros=self.zeros,disk_release=self.release)
  exec(src,env)
  return env['jacobian_for_prompt']

def matrix_stats(J):
 n2=diag2=identity2=0.
 D=J.shape[0]
 for i in range(0,D,64):
  x=J[i:i+64].float();assert torch.isfinite(x).all(),'non-finite Jacobian';n2+=float(x.square().sum())
  r=torch.arange(i,min(i+64,D));v=x[torch.arange(len(r)),r]
  diag2+=float(v.square().sum());identity2+=float(v.sum())
 return {'frobenius_over_sqrt_d':(n2/D)**.5,'diagonal_energy_fraction':diag2/max(n2,1e-30),'distance_from_identity_over_sqrt_d':max(0,(n2+D-2*identity2)/D)**.5}

def pair_stats(J,P):
 # FP64 block reductions avoid loss of small off-diagonal terms in a
 # single 26-million-element FP32 norm reduction.
 xx=yy=xy=dd=0.
 for i in range(0,J.shape[0],64):
  a=J[i:i+64].double();b=P[i:i+64].double()
  xx+=float(a.square().sum());yy+=float(b.square().sum());xy+=float((a*b).sum());dd+=float((a-b).square().sum())
 return {'cosine_to_previous_snapshot':xy/max((xx*yy)**.5,1e-300),'relative_difference_from_previous':(dd/max(xx,1e-300))**.5}

def available():return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024/1024**3

def atomic_json(path,data):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(path)

def fit_stream(lm,prompts,indices,root,dim_batch):
 root=Path(root);root.mkdir(exist_ok=True)
 D=lm.d_model;layers=list(range(lm.n_layers-1));means={}
 statepath=root/'state.json'
 state=json.loads(statepath.read_text()) if statepath.exists() else {'completed':0,'indices':indices}
 assert state['indices']==indices
 if state.get('updating'):
  for l in state.get('backed_up',[]):
   shutil.copyfile(root/f'prev-{l}.bin',root/f'mean-{l}.bin')
  state.pop('updating',None);state['backed_up']=[];atomic_json(statepath,state)
 for l in layers:
  p=root/f'mean-{l}.bin'
  if not p.exists():
   with open(p,'wb') as f:f.truncate(D*D*4)
  means[l]=np.memmap(p,dtype='float32',mode='r+',shape=(D,D))
 resources={'low':available()}
 def sample_resources():
  while True:resources['low']=min(resources['low'],available());time.sleep(.25)
 threading.Thread(target=sample_resources,daemon=True).start()
 for n,idx in enumerate(indices,1):
  if n<=state['completed']:continue
  start=time.time();resources['low']=available();torch.cuda.reset_peak_memory_stats()
  with tempfile.TemporaryDirectory(dir=root,prefix='jac-') as td:
   disk=DiskJacobians(td);J,T,V=disk.function()(lm,prompts[idx]['text'],layers,target_layer=63,dim_batch=dim_batch,max_seq_len=128)
   delta2=mean2=0.;stats={}
   state.update(updating=n,backed_up=[]);atomic_json(statepath,state)
   for l in layers:
    shutil.copyfile(root/f'mean-{l}.bin',root/f'prev-{l}.bin')
    with open(root/f'prev-{l}.bin','r+b') as f:
     os.fsync(f.fileno());os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
    state['backed_up'].append(l);atomic_json(statepath,state)
    mean=torch.from_numpy(means[l]);cur=J[l]
    for i in range(0,D,64):
     old=mean[i:i+64].clone();change=(cur[i:i+64]-old)/n
     mean[i:i+64].add_(change);delta2+=float(change.square().sum());mean2+=float(mean[i:i+64].square().sum())
    stats[l]=matrix_stats(cur)
    means[l].flush();means[l]._mmap.madvise(mmap.MADV_DONTNEED)
    disk.maps[l]._mmap.madvise(mmap.MADV_DONTNEED)
   state.update(completed=n,updating=None,backed_up=[]);atomic_json(statepath,state)
   rec={'prompt_idx':idx,'lang':prompts[idx]['lang'],'local_N':n,'min_avail_GiB':resources['low'],'peak_cuda_GiB':torch.cuda.max_memory_allocated()/1024**3,'elapsed_sec':time.time()-start,'tokens':T,'valid_positions':V,'prompt_norm':max(s['frobenius_over_sqrt_d'] for s in stats.values()),'mean_rel_change':(delta2/max(mean2,1e-30))**.5,'layer_stats':stats}
   with open(root/'convergence.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
   print('FIT_PROMPT_DONE',idx,n,rec['elapsed_sec'],flush=True)
   del J,cur,mean;gc.collect();torch.cuda.empty_cache()
   if n in [1,2,5,10,20,25,30,50]:
    lens=JacobianLens({l:torch.from_numpy(means[l]) for l in layers},n_prompts=n,d_model=D)
    lens.save(str(root/f'lens_local_n{n}.pt'))
    (root/f'lens_local_n{n}.indices.json').write_text(json.dumps(indices[:n]))
    del lens
    for a in means.values():a._mmap.madvise(mmap.MADV_DONTNEED)
