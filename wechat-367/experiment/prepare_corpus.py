"""CPU-only streaming corpus; exact EN/ZH token quotas and document holdout."""
import os,json,hashlib,time
from pathlib import Path
os.environ.pop('HF_HUB_OFFLINE',None);os.environ.pop('TRANSFORMERS_OFFLINE',None)
from datasets import load_dataset
from transformers import AutoTokenizer
R=Path(__file__).resolve().parent;T=200704;H=51200;CHUNK=512
tok=AutoTokenizer.from_pretrained('/home/lmxxf/work/models/Qwen3.8-27B-FP8',local_files_only=True)
records=[];seen=set()
for lang,repo,cfg in [('en','Salesforce/wikitext','wikitext-103-raw-v1'),('zh','wikimedia/wikipedia','20231101.zh')]:
 counts={'fit':0,'heldout':0};targets={'fit':T//2,'heldout':H//2};article=None;article_index=-1
 ds=load_dataset(repo,cfg,split='train',streaming=True)
 for i,row in enumerate(ds):
  text=row['text'].strip()
  if lang=='en':
   if text.startswith('= ')and text.endswith(' =')and text.count('=')==2:article=text.strip('= ');article_index+=1;continue
   if not article:continue
   key=article;split='heldout'if article_index%5==0 else'fit'
  else:key=str(row.get('id',i));split='heldout'if i%5==0 else'fit'
  if counts[split]>=targets[split]or len(text)<180:continue
  ids=tok.encode(text,add_special_tokens=False)
  if len(ids)<128:continue
  # Same source document/article is never shared between fit and heldout.
  for off in range(0,min(len(ids),4096),CHUNK):
   part=ids[off:off+CHUNK]
   if len(part)<128:continue
   take=min(len(part),targets[split]-counts[split])
   if take<=0:break
   part=part[:take]
   records.append({'lang':lang,'split':split,'source':repo,'config':cfg,'source_row':i,'document_id':key,'offset':off,'token_ids':part,'tokens':[tok.decode([t])for t in part]});counts[split]+=take
  if all(counts[k]>=targets[k]for k in targets):break
 print('CORPUS_LANG',lang,counts,flush=True)
 # Interleave later, not separate-language layer fits.
assert sum(len(r['token_ids'])for r in records if r['split']=='fit')==T
assert sum(len(r['token_ids'])for r in records if r['split']=='heldout')==H
for lang in ['en','zh']:
 fit={r['document_id']for r in records if r['lang']==lang and r['split']=='fit'};held={r['document_id']for r in records if r['lang']==lang and r['split']=='heldout'};assert not fit&held
ordered=[]
for split in ['fit','heldout']:
 a=[r for r in records if r['split']==split and r['lang']=='en'];b=[r for r in records if r['split']==split and r['lang']=='zh']
 for i in range(max(len(a),len(b))):
  for x in [a,b]:
   if i<len(x):ordered.append(x[i])
p=R/'corpus.jsonl';p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n'for r in ordered))
(R/'corpus_manifest.json').write_text(json.dumps({'fit_tokens':T,'heldout_tokens':H,'fit_tokens_per_language':T//2,'heldout_tokens_per_language':H//2,'max_sequence':512,'records':len(ordered),'document_disjoint':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'time':time.time()},indent=2))
print('CORPUS_DONE',len(ordered),flush=True)
# datasets/pyarrow streaming teardown exhibited a PyGILState finalizer error in365.
# All files are closed and validated before this successful exit.
os._exit(0)
