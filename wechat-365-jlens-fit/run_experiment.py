import os,sys,time,json,threading,subprocess,signal,gc,logging,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
G=1024**3

def avail():
 return int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024/G

def monitor():
 while True:
  if avail()<22: print('INTERNAL_MEMORY_ABORT',avail(),flush=True);os._exit(73)
  time.sleep(.25)

def supervise(args):
 if avail()<=100: subprocess.run(['sudo','-n','sh','-c','sync; echo 3 > /proc/sys/vm/drop_caches'],check=True)
 assert avail()>100,avail()
 p=subprocess.Popen([sys.executable,str(Path(__file__)),*args],start_new_session=True)
 low=avail()
 while p.poll() is None:
  a=avail();low=min(a,low)
  if a<20: os.killpg(p.pid,signal.SIGKILL)
  (ROOT/'watchdog.json').write_text(json.dumps({'pid':p.pid,'minimum_available_GiB':low,'current_available_GiB':a,'time':time.time()}))
  time.sleep(.25)
 sys.exit(p.returncode)

if sys.argv[1]=='supervise':supervise(sys.argv[2:])
signal.signal(signal.SIGINT,signal.default_int_handler)
threading.Thread(target=monitor,daemon=True).start()
if sys.argv[1]=='evaluate':
 import runpy
 runpy.run_path(str(ROOT/'evaluate_lenses.py'),run_name='__main__')
 sys.exit(0)
import torch
sys.path.insert(0,str(ROOT/'upstream'))
sys.path.insert(0,'/home/lmxxf/work/interp-curvature-exp')
from loader_reference import load_model
from jlens import from_hf
from jlens.fitting import jacobian_for_prompt
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s')
torch.set_num_threads(8)
a=argparse.ArgumentParser();a.add_argument('mode');a.add_argument('--parity',type=int,default=0);a.add_argument('--checkpoint',action='store_true');a.add_argument('--pilot',type=int,default=0);a.add_argument('--batch',type=int,default=8);args=a.parse_args()
tok,model=load_model('Qwen3.8-27B-FP8')
lm=from_hf(model,tok,force_bos=False)
print('ADAPTER',repr(lm),flush=True)
if args.checkpoint:
 from torch.utils.checkpoint import checkpoint
 for layer in lm.layers:
  orig=layer.forward
  def wrapped(*x,_orig=orig,**kw):
   return checkpoint(_orig,*x,use_reentrant=False,**kw)
  layer.forward=wrapped
# Timing only; the derivative operation and official estimator are unchanged.
original_grad=torch.autograd.grad
progress={'passes':0,'started':None,'min_avail':avail()}
class PilotDone(Exception):pass
def timed_grad(*x,**kw):
 t=time.time();y=original_grad(*x,**kw);torch.cuda.synchronize()
 progress['passes']+=1;progress['min_avail']=min(progress['min_avail'],avail())
 if progress['started'] is None:progress['started']=t
 if progress['passes']%10==0 or progress['passes']==1:
  print('BACKWARD_PROGRESS',progress['passes'],time.time()-progress['started'],avail(),flush=True)
 if args.pilot and progress['passes']>=args.pilot:
  elapsed=time.time()-progress['started']
  result=dict(progress,dim_batch=args.batch,checkpoint=args.checkpoint,backward_seconds=elapsed,extrapolated_prompt_seconds=elapsed/progress['passes']*((5120+args.batch-1)//args.batch),peak_cuda_GiB=torch.cuda.max_memory_allocated()/G,complete_jacobian=False)
  (ROOT/f'pilot_b{args.batch}_cp{args.checkpoint}.json').write_text(json.dumps(result,indent=2))
  print('PILOT_DONE',result,flush=True);raise PilotDone()
 return y
torch.autograd.grad=timed_grad
if args.mode=='fit':
 from stream_fitting import fit_stream
 prompts=json.loads((ROOT/'prompts_100.json').read_text())
 fit_stream(lm,prompts,list(range(args.parity,100,2)),ROOT/('fit_even' if args.parity==0 else 'fit_odd'),args.batch)
 sys.exit(0)
prompt=json.loads((ROOT/'prompts_100.json').read_text())[0]['text']
assert len(tok.encode(prompt))>=160
start=time.time();torch.cuda.reset_peak_memory_stats()
low=[avail()]
def track():
 while True:low[0]=min(low[0],avail());time.sleep(.25)
threading.Thread(target=track,daemon=True).start()
try:
 J,T,V=jacobian_for_prompt(lm,prompt,list(range(63)),target_layer=63,dim_batch=args.batch,max_seq_len=128)
except PilotDone:
 sys.exit(0)
torch.cuda.synchronize()
result={'dim_batch':args.batch,'elapsed_seconds':time.time()-start,'tokens':T,'valid_positions':V,'peak_cuda_GiB':torch.cuda.max_memory_allocated()/G,'min_available_GiB':low[0],'norms':{l:float(j.norm()/5120**.5) for l,j in J.items()}}
(ROOT/f'smoke_b{args.batch}.json').write_text(json.dumps(result,indent=2));print('SMOKE_DONE',result,flush=True)
from jlens import JacobianLens
JacobianLens(J,n_prompts=1,d_model=5120).save(str(ROOT/f'smoke_b{args.batch}.pt'))
