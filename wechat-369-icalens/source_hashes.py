import hashlib,json,time,sys
from pathlib import Path
R=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
role='slave'if '--role=slave'in sys.argv else'merged_main'
layers=([16,41,63]+[i for i in range(64)if i not in [0,16,38,41,56,63]][1::2])if role=='slave'else list(range(64))
items={}
for l in layers:
 p=R/f'L{l:02d}'
 for n in ['complete.json','statistics.json','oriented.safetensors','saelens_adapter.safetensors',f'native/artifacts/resid_post/layer_{l:02d}.safetensors','native/icalens.json','vocabulary_readouts.json','polysemy_analysis.json','polysemy_probes.npy','polysemy_readouts.json','contexts_decoded.json']:
  f=p/n
  if role=='slave'and n in ['polysemy_analysis.json','polysemy_probes.npy','polysemy_readouts.json','contexts_decoded.json']:continue
  assert f.exists(),str(f);items[str(f.relative_to(R))]={'bytes':f.stat().st_size,'sha256':sha(f)}
 if l in [0,16,38,41,56,63]:
  f=p/'steering.json';items[str(f.relative_to(R))]={'bytes':f.stat().st_size,'sha256':sha(f)}
name='source_sha256_slave'if role=='slave'else'source_sha256';q=R/(name+'.tmp');q.write_text(json.dumps({'role':role,'time':time.time(),'layers':layers,'files':items},indent=2));q.replace(R/(name+'.json'));print('SOURCE_SHA256_DONE',len(items),flush=True)
