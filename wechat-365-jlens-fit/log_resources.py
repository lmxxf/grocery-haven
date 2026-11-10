import time,json
from pathlib import Path
r=Path(__file__).resolve().parent
with open(r/'resource_timeseries.jsonl','a',buffering=1) as f:
 while True:
  a=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024/1024**3
  f.write(json.dumps({'time':time.time(),'MemAvailable_GiB':a})+'\n');time.sleep(.25)
