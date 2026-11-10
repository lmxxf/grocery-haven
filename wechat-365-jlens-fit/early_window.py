"""Take one checkpoint boundary, release main model, evaluate, then resume.
The slave never stops. Main completed prompt count is preserved.
"""
import os,sys,json,time,subprocess,signal
from pathlib import Path
R=Path(__file__).resolve().parent;P='/home/lmxxf/work/interp-curvature-exp/venv/bin/python'
def status(s,**kw):
 p=R/'early_status.json';q=p.with_suffix('.tmp');q.write_text(json.dumps({'status':s,'time':time.time(),**kw}));q.replace(p)
def run(cmd,name,env=None):
 with open(R/name,'a') as f:x=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,env=env)
 if x.returncode:raise RuntimeError((cmd,x.returncode))
status('waiting_for_main_checkpoint')
snapshot=R/'fit_even/lens_local_n1.pt'
while True:
 if snapshot.exists() and time.time()-snapshot.stat().st_mtime>1:
  state=json.loads((R/'fit_even/state.json').read_text());pid=json.loads((R/'watchdog.json').read_text())['pid']
  opened=False
  for fd in Path(f'/proc/{pid}/fd').glob('*'):
   try:opened|=Path(os.readlink(fd))==snapshot
   except OSError:pass
  if state['completed']>=1 and not opened:break
 time.sleep(.2)
assert b'run_experiment.py fit' in Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ')
# Stop orchestration only; its independently supervised fitting child remains live.
controller=int((R/'pipeline.pid').read_text())
os.kill(controller,signal.SIGTERM)
status('pausing_main_at_checkpoint',completed_prompts=state['completed'],model_pid=pid)
(R/'pipeline_status.json').write_text(json.dumps({'status':'early_evaluation','time':time.time()}))
os.kill(pid,signal.SIGINT)
# Legacy nohup workers inherited SIGINT ignored; future workers explicitly reset it.
if int(Path(f'/proc/{pid}/status').read_text().split('SigIgn:')[1].splitlines()[0].strip(),16)&2:
 os.kill(pid,signal.SIGTERM)
for _ in range(120):
 if not Path(f'/proc/{pid}').exists():break
 time.sleep(.5)
else:raise RuntimeError('main model did not exit cleanly; refusing a second load')
try:
 status('merging')
 run(['rsync','-a','--include=lens_local_n*.pt','--exclude=*',f'169.254.30.81:{R}/fit_odd/',str(R/'early_odd')+'/'],'early_copy.log')
 run([P,'-u','merge_early.py'],'early_merge.log')
 status('evaluating')
 env=dict(os.environ,JLENS_EARLY='1',TRITON_CACHE_DIR=str(R/'triton-cache'))
 run([P,'-u','run_experiment.py','supervise','evaluate'],'early_evaluation.log',env)
 status('evaluation_complete',main_completed_prompts=state['completed'])
except BaseException as e:
 status('evaluation_failed',error=repr(e));raise
finally:
 with open(R/'pipeline.log','a') as f:
  resumed=subprocess.Popen(['/usr/bin/python3','-u','remote_pipeline.py'],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 (R/'pipeline.pid').write_text(str(resumed.pid))
 print('MAIN_PIPELINE_RESUMED',resumed.pid,flush=True)
