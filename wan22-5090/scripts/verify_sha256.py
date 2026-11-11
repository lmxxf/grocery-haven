import hashlib,sys,time,json
from pathlib import Path
p=Path(sys.argv[1]);start=time.perf_counter();h=hashlib.sha256()
with p.open('rb')as f:
 for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
digest=h.hexdigest();elapsed=time.perf_counter()-start
print(json.dumps({'file':str(p),'bytes':p.stat().st_size,'sha256':digest,'seconds':elapsed,'MB_per_second':p.stat().st_size/max(elapsed,1e-9)/1e6}))
if len(sys.argv)>2 and digest.lower()!=sys.argv[2].lower():sys.exit(2)
