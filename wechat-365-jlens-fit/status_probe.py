"""Read-only Spark probe, no torch/CUDA imports."""
import json,time,os,socket
from pathlib import Path
r=Path(__file__).resolve().parent

def read(p,default=None):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return default
s={'time':time.time(),'hostname':socket.gethostname(),'available_GiB':int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024/1024**3,'pipeline':read(r/'pipeline_status.json',{})}
for tag in ['even','odd']:
 st=read(r/f'fit_{tag}/state.json')
 if st is not None:s[tag]={'completed':st.get('completed',0),'updating':st.get('updating')}
w=read(r/'watchdog.json',{});pid=w.get('pid',-1);s['model_pid']=pid;s['model_alive']=Path(f'/proc/{pid}').exists();s['watchdog_age']=time.time()-w.get('time',0);s['process_min_available_GiB']=w.get('minimum_available_GiB')
for tag in ['even','odd']:
 p=r/f'fit_{tag}.log'
 if p.exists():
  with open(p,'rb') as f:f.seek(max(0,p.stat().st_size-2500));tail=f.read().decode(errors='replace').splitlines()
  s[f'{tag}_log_age']=time.time()-p.stat().st_mtime;s[f'{tag}_tail']=tail[-1]if tail else ''
print(json.dumps(s))
