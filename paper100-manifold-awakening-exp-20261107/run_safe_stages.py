#!/usr/bin/env python3
"""Independent external watchdog + sequential process lifecycle barrier."""
import os,time,sys,json,signal,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent
PY='/home/lmxxf/work/interp-curvature-exp/venv/bin/python'
def avail():return int(next(l.split()[1]for l in Path('/proc/meminfo').read_text().splitlines()if l.startswith('MemAvailable:')))/1024**2
def main():
 for stage in sys.argv[1:] or ['qwen27b','qwen35b_base','qwen35b_post','qwen06b','analyze']:
  subprocess.run(['sudo','-n','sh','-c','sync; echo 3 > /proc/sys/vm/drop_caches'],check=True)
  a=avail()
  anchor_only=stage.endswith(':anchors');actual_stage=stage.split(':')[0]
  if stage!='analyze' and a<=105:raise RuntimeError(f'{stage}: MemAvailable {a:.3f} <=105 GiB')
  print(time.ctime(),'START',stage,a,flush=True)
  with (R/f'{stage}.log').open('a')as log:
   child=subprocess.Popen([PY,str(R/'run_paper100_manifold_awakening.py'),'--stage',actual_stage]+(['--anchors-only'] if anchor_only else []),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   minimum=a
   while child.poll() is None:
    a=avail();minimum=min(a,minimum)
    if a<22:
     os.killpg(child.pid,signal.SIGKILL);child.wait();raise RuntimeError(f'EXTERNAL MEMORY ABORT: {stage} {a}')
    time.sleep(.2)
   print(time.ctime(),'EXIT',stage,child.returncode,'min_available_GiB',minimum,flush=True)
   with (R/'stage_resources.jsonl').open('a')as f:f.write(json.dumps({'stage':stage,'returncode':child.returncode,'minimum_available_GiB':minimum,'after_exit_available_GiB':avail()})+'\n')
   if child.returncode:raise RuntimeError(f'{stage} failed, see {stage}.log')
  # wait() above has reaped the model process; CUDA context is gone before cache drop.
if __name__=='__main__':main()
