"""Persistent remote orchestrator. No model subprocess starts below 100 GiB.
Fit child is independent session with two watchdogs. Evaluation is guarded too.
"""
import os,json,sys,time,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent
P='/home/lmxxf/work/interp-curvature-exp/venv/bin/python'
os.environ['TRITON_CACHE_DIR']=str(R/'triton-cache')
def write(status,**kw):(R/'pipeline_status.json').write_text(json.dumps(dict(status=status,time=time.time(),**kw)))
def run(cmd,log):
 with open(R/log,'a') as f:
  p=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError((cmd,p.returncode))
def wait_main_smoke():
 while not (R/'smoke_b1.json').exists():
  write('waiting_for_smoke');time.sleep(10)
 # Wait for its lens serialization and complete process teardown.
 while True:
  try:data=json.loads((R/'watchdog.json').read_text());pid=data['pid']
  except (ValueError,FileNotFoundError):time.sleep(1);continue
  try:os.kill(pid,0)
  except ProcessLookupError:break
  time.sleep(5)
 smoke=json.loads((R/'smoke_b1.json').read_text())
 assert smoke['min_available_GiB']>22,smoke
 # batch1 is a control; production batch2 uses memory-mapped matrices,
 # independently calibrated on slave. The corpus-preparation CPU process
 # temporarily lowered the batch1 control below the 45-GiB selection margin.
try:
 wait_main_smoke();write('fitting_even')
 run([P,'-u','run_experiment.py','supervise','fit','--batch','2','--parity','0'],'fit_even.log')
 write('waiting_for_odd')
 while True:
  r=subprocess.run(['ssh','-o','ConnectTimeout=10','169.254.30.81',f'cat {R}/fit_odd/state.json'],capture_output=True,text=True)
  if r.returncode==0:
   try:done=json.loads(r.stdout).get('completed')==50
   except ValueError:done=False
   if done:
    # state commits before final snapshot serialization; wait for process exit.
    check=subprocess.run(['ssh','169.254.30.81','python3',str(R/'check_odd_done.py')],capture_output=True,text=True)
    if check.returncode==0:break
  time.sleep(30)
 write('copying_odd')
 run(['rsync','-a',f'169.254.30.81:{R}/fit_odd/',str(R/'fit_odd')+'/', '--include=lens_local_n*.pt','--include=*.indices.json','--include=convergence.jsonl','--include=state.json','--exclude=*'],'copy_odd.log')
 run(['rsync','-a',f'169.254.30.81:{R}/resource_timeseries.jsonl',str(R/'resource_timeseries_odd.jsonl')],'copy_resources_odd.log')
 write('merging');run([P,'-u','merge_analyze.py'],'merge.log')
 write('evaluating');run([P,'-u','run_experiment.py','supervise','evaluate'],'evaluation.log')
 write('complete')
except BaseException as e:
 write('failed',error=repr(e));raise
