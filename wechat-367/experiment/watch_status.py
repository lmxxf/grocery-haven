import json,subprocess,time,sys,concurrent.futures
from pathlib import Path
R=Path(__file__).resolve().parent

def get(role):
 cmd='python3 /home/lmxxf/work/ica-lens-qwen38-27b/status_snapshot.py '+role
 if role=='slave':cmd='ssh -o BatchMode=yes 169.254.30.81 '+cmd
 p=subprocess.run(['ssh','-o','BatchMode=yes','lmxxf@192.168.31.198',cmd],text=True,capture_output=True,timeout=30);p.check_returncode();return json.loads(p.stdout)
def snapshot():
 with concurrent.futures.ThreadPoolExecutor(2)as e:a=list(e.map(get,['main','slave']))
 d={'time':time.time(),'nodes':a,'completed':sum(len(v['completed'])for v in a),'readouts':sum(len(v['readouts'])for v in a),'acceptance':'NOT_YET_VALIDATED'};p=R/'takeover_status.json';q=p.with_suffix('.tmp');q.write_text(json.dumps(d,indent=2));q.replace(p);print(time.strftime('%F %T'),'completed',d['completed'],'readouts',d['readouts'],'states',[v['status']['state']for v in a],'available',[round(v['available_GiB'],1)for v in a],flush=True)
 if any(v['status']['state']=='failed'for v in a):raise RuntimeError('REMOTE_WORKER_FAILED')
 return d
if __name__=='__main__':
 while True:
  d=snapshot()
  if '--once'in sys.argv or all(v['status']['state']=='complete'for v in d['nodes']):break
  time.sleep(30)
