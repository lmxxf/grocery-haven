"""366 remote-only sequential forward/hook experiments with memory guards."""
import os,sys,time,json,signal,subprocess,threading,importlib,traceback
from pathlib import Path
R=Path(__file__).resolve().parent
G=1024**3

def avail():return int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024/G

def save(name,value):
 p=R/name;q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False));q.replace(p)

if len(sys.argv)>1 and sys.argv[1]=='supervise':
 if avail()<=100:subprocess.run(['sudo','-n','sh','-c','sync; echo 3 > /proc/sys/vm/drop_caches'],check=True)
 assert avail()>100,avail()
 p=subprocess.Popen([sys.executable,'-u',str(R/'pipeline.py'),*sys.argv[2:]],cwd=R,start_new_session=True)
 low=avail()
 while p.poll() is None:
  a=avail();low=min(a,low)
  if a<20:print('EXTERNAL_ABORT',a,flush=True);os.killpg(p.pid,signal.SIGKILL)
  save('watchdog.json',{'pid':p.pid,'time':time.time(),'minimum_available_GiB':low,'available_GiB':a});time.sleep(.25)
 sys.exit(p.returncode)

def internal():
 while True:
  if avail()<22:print('INTERNAL_ABORT',avail(),flush=True);os._exit(73)
  time.sleep(.25)
threading.Thread(target=internal,daemon=True).start()
signal.signal(signal.SIGINT,signal.default_int_handler)
os.environ['TRITON_CACHE_DIR']=str(R/'triton-cache')
import torch
sys.path.insert(0,'/home/lmxxf/work/jlens-qwen38-27b/upstream')
from loader_reference import load_model
from jlens import from_hf
from jlens.hooks import ActivationRecorder
torch.set_num_threads(8);torch.manual_seed(20261110)
class Context:
 def __init__(self):
  self.tok,self.model=load_model('Qwen3.8-27B-FP8');self.lm=from_hf(self.model,self.tok,force_bos=False)
  self.checkpoints={n:torch.load(f'/home/lmxxf/work/jlens-qwen38-27b/lens_n{n}.pt',map_location='cpu',mmap=True,weights_only=True)for n in [1,100]}
  self.dirs={};self.save=save;self.root=R
 def ids(self,s):return self.tok.encode(s,add_special_tokens=False)
 def single(self,s):
  a=self.ids(s);return a[0]if len(a)==1 else None
 @torch.inference_mode()
 def capture(self,ids,all_positions=False):
  x=torch.tensor([ids],device='cuda')
  with ActivationRecorder(self.lm.layers,at=list(range(64)))as rec:
   self.lm.forward(x)
   out={l:(rec.activations[l][0]if all_positions else rec.activations[l][0,-1:]).float().cpu()for l in range(64)}
  return out
 @torch.inference_mode()
 def final(self,ids):
  out=self.model(torch.tensor([ids],device='cuda'),use_cache=False)
  return out.logits[0,-1].float()
 @torch.inference_mode()
 def generate(self,ids,max_new=32):
  x=torch.tensor([ids],device='cuda')
  out=self.model.generate(x,max_new_tokens=max_new,do_sample=False,use_cache=True,pad_token_id=self.tok.eos_token_id)
  new=out[0,len(ids):].tolist();return {'text':self.tok.decode(new,skip_special_tokens=True),'token_ids':new,'tokens':len(new),'hit_limit':len(new)==max_new}
try:
 save('status.json',{'phase':'loading','time':time.time()});c=Context()
 if len(sys.argv)>1 and sys.argv[1]=='arithmetic_check':
  c.dirs=torch.load(R/'concept_directions.pt',map_location='cpu',weights_only=True)
  import arithmetic_position_check
  arithmetic_position_check.run(c)
  save('status.json',{'phase':'complete','time':time.time()});sys.exit(0)
 if len(sys.argv)>1 and sys.argv[1]=='supplement':
  c.dirs=torch.load(R/'concept_directions.pt',map_location='cpu',weights_only=True)
  import exp4_dosecheck
  exp4_dosecheck.run(c)
  save('status.json',{'phase':'complete','time':time.time()});sys.exit(0)
 for i in range(1,5):
  save('status.json',{'phase':f'experiment{i}','time':time.time()})
  while not (R/f'exp{i}.py').exists():time.sleep(.5)
  importlib.import_module(f'exp{i}').run(c)
  print('EXPERIMENT_DONE',i,flush=True)
 save('status.json',{'phase':'complete','time':time.time()})
except Exception as e:
 save('status.json',{'phase':'failed','error':repr(e),'traceback':traceback.format_exc(),'time':time.time()});raise
