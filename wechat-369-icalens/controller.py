#!/usr/bin/env python3
import os,sys,time,json,subprocess,signal
from pathlib import Path
R=Path(__file__).resolve().parent;os.chdir(R)
def avail():return int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))/1048576
def status(**x):
 p=R/'status.json';q=p.with_suffix('.tmp');q.write_text(json.dumps(dict(role=sys.argv[1],time=time.time(),available_GiB=avail(),**x),indent=2));q.replace(p)
def run(args):
 subprocess.run(['sudo','-n','sh','-c','echo 3 > /proc/sys/vm/drop_caches'],check=True)
 if avail()<100:raise RuntimeError(f'Insufficient start MemAvailable: {avail()} GiB')
 status(state='running',command=args)
 with open(R/'worker.log','a',buffering=1)as log:
  p=subprocess.Popen([sys.executable,*args],start_new_session=True,stdout=log,stderr=log)
  while p.poll()is None:
   if avail()<20:
    os.killpg(p.pid,signal.SIGKILL);p.wait();raise RuntimeError('20 GiB independent watchdog killed process group')
   time.sleep(.25)
  if p.returncode:raise RuntimeError(f'Child failed {p.returncode}: {args}')
role=sys.argv[1];priority=[0,38,56]if role=='main'else[16,41,63];rest=[i for i in range(64)if i not in [0,16,38,41,56,63]][0 if role=='main'else 1::2]
try:
 for phase,layers in [('priority',priority),('remaining',rest)]:
  missing=[l for l in layers if not(R/f'L{l:02d}'/'complete.json').exists()]
  extraction=[l for l in missing if not(R/f'L{l:02d}'/'extracted.json').exists()]
  if extraction:run(['worker.py','extract',*map(str,extraction)])
  for l in missing:
   run(['worker.py','fit',str(l)])
   run(['analyze.py','readout',str(l)])
   if phase=='priority':run(['analyze.py','steer',str(l)])
   for s in ['fit','heldout']:(R/f'L{l:02d}'/f'{s}.npy').unlink(missing_ok=True)
  status(state=phase+'_complete',layers=layers)
 status(state='complete',layers=priority+rest)
except BaseException as e:
 status(state='failed',error=repr(e));raise
