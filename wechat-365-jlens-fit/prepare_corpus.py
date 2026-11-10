import os,json,time
os.environ.pop('HF_HUB_OFFLINE',None);os.environ.pop('TRANSFORMERS_OFFLINE',None)
from datasets import load_dataset
from transformers import AutoTokenizer
from pathlib import Path
root=Path(__file__).resolve().parent
tok=AutoTokenizer.from_pretrained('/home/lmxxf/work/models/Qwen3.8-27B-FP8',local_files_only=True)
sets=[('en','Salesforce/wikitext','wikitext-103-raw-v1'),('zh','wikimedia/wikipedia','20231101.zh')]
col={}
for lang,repo,cfg in sets:
 out=[];article=None;chosen=set()
 ds=load_dataset(repo,cfg,split='train',streaming=True)
 for i,r in enumerate(ds):
  text=r['text'].strip()
  if lang=='en':
   if text.startswith('= ') and text.endswith(' =') and text.count('=')==2:
    article=text.strip('= ').strip();continue
   if article in chosen:continue
  if len(text)<(800 if lang=='en' else 350):continue
  # Keep natural article text and avoid serially repeating adjoining paragraphs.
  text=text[:5000]
  ids=tok.encode(text,add_special_tokens=False)
  if len(ids)<160:continue
  out.append(dict(lang=lang,text=text,token_count=len(ids),source=repo,config=cfg,source_row=i,title=(article if lang=='en' else r.get('title'))))
  if lang=='en':chosen.add(article)
  if len(out)==50:break
 col[lang]=out
 print(lang,len(out),flush=True)
rows=[]
for i in range(50):
 for lang in ['en','zh']:rows.append(dict(idx=len(rows),**col[lang][i]))
(root/'prompts_100.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
