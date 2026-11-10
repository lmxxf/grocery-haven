"""Remote-only bounded readouts; official benchmark prompts, explicit token eligibility."""
import os,sys,json,time,gc,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'upstream'));sys.path.insert(0,'/home/lmxxf/work/interp-curvature-exp')
import torch
from loader_reference import load_model
from jlens import from_hf
from jlens.hooks import ActivationRecorder
from jlens.examples import EXAMPLES

def avail():return int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024/1024**3
def watch():
 while True:
  if avail()<22:os._exit(73)
  time.sleep(.25)
threading.Thread(target=watch,daemon=True).start()
torch.set_num_threads(8)
tok,model=load_model('Qwen3.8-27B-FP8');lm=from_hf(model,tok,force_bos=False)
items=[]
for group in ['multihop','multilingual']:
 for item in json.loads((ROOT/'upstream/data/evaluations'/f'lens-eval-{group}.json').read_text())['items']:
  items.append(dict(item,group=group))
extra=[
 ('ascii-face',next(e.prompt for e in EXAMPLES if e.slug=='ascii-face'),['nose','face']),
 ('boot-currency-en','Fact: The currency used in the country shaped like a boot is',['Italy']),
 ('boot-currency-zh','常识：形状像一只靴子的欧洲国家使用的法定货币是',['意大利','Italy']),
 ('spider-zh','猜谜：会结网捕食飞虫、长有八条腿的节肢动物是',['蜘蛛','spider']),
 ('madrid-zh','中国的首都是北京，那么与法国接壤、首都位于马德里的国家是',['西班牙','Spain']),
 ('honey-en','Fact: The flying insect that makes honey lives in a',['bee']),
 ('nile-en','Fact: The continent containing the country with the pyramids at Giza is',['Egypt']),
 ('tokyo-zh','常识：首都为东京的国家使用的货币是',['日本','Japan'])]
for name,prompt,concepts in extra:items.append(dict(name=name,prompt=prompt,intermediates=concepts,group='representative'))

def variants(word):
 out={}
 for w in [word,word.lower(),word.capitalize()]:
  for v in [w,' '+w]:
   ids=tok.encode(v,add_special_tokens=False)
   if len(ids)==1:out[ids[0]]=v
 return sorted(out)
for it in items:it['concept_token_ids']={c:variants(c) for c in it['intermediates']}
# Readout is the last prompt position, before generating the target. No target leakage.
# Official data defines target only to identify that boundary; no continuation is injected.
hidden={l:[] for l in range(64)}
with torch.inference_mode():
 for it in items:
  ids=lm.encode(it['prompt'],max_length=512)
  with ActivationRecorder(lm.layers,at=list(range(64))) as rec:
   lm.forward(ids)
   for l in range(64):hidden[l].append(rec.activations[l][0,-1].float().cpu())
  del rec;torch.cuda.empty_cache()
 hidden={l:torch.stack(h) for l,h in hidden.items()}
output={'items':items,'stages':{},'metric':'single-token surface variants; min rank over layers; ties use 1 + strictly greater logits','readout_position':'last prompt token; raw text; no chat template','layer_band':[0,63]}
early=os.environ.get('JLENS_EARLY')=='1'
output_path=ROOT/('early_evaluation_results.json' if early else 'evaluation_results.json')
paths=[('vanilla',None)]+[(f'n{n}',ROOT/f'lens_n{n}.pt') for n in [1,2,4,10,20,50,100] if (ROOT/f'lens_n{n}.pt').exists()]
for name,path in paths:
 stage={'items':[{**{'name':it['name'],'group':it['group']},'layers':{},'min_ranks':{c:None for c in it['intermediates']}} for it in items]}
 checkpoint=torch.load(path,map_location='cpu',mmap=True,weights_only=True) if path else None
 with torch.inference_mode():
  for l in range(64):
   h=hidden[l].cuda()
   if checkpoint and l!=63:
    J=checkpoint['J'][l].to(device='cuda',dtype=torch.float32)
    h=h@J.T;del J
   logits=lm.unembed(h).float();tops=logits.topk(5,dim=-1)
   for i,it in enumerate(items):
    ranks={c:(1+int((logits[i]>logits[i,ids].max()).sum()) if ids else None) for c,ids in it['concept_token_ids'].items()}
    row={'ranks':ranks}
    if it['group']=='representative':row['top5']=[{'token_id':int(t),'text':tok.decode([int(t)]),'logit':float(v)} for t,v in zip(tops.indices[i],tops.values[i])]
    stage['items'][i]['layers'][l]=row
    for c,r in ranks.items():
     if r is not None:
      old=stage['items'][i]['min_ranks'][c];stage['items'][i]['min_ranks'][c]=r if old is None else min(r,old)
   del h,logits,tops;torch.cuda.empty_cache()
 stage['metrics']={}
 for group in ['multihop','multilingual']:
  rows=[r for r in stage['items'] if r['group']==group]
  eligible=[[v for v in r['min_ranks'].values() if v is not None] for r in rows]
  usable=[r for r in eligible if r]
  stage['metrics'][group]={'items':len(rows),'eligible_items':len(usable),'excluded_multitoken_concepts':sum(v is None for r in rows for v in r['min_ranks'].values()),**{f'pass@{k}':sum(sum(v<=k for v in r)/len(r) for r in usable)/len(usable) if usable else None for k in [1,5,10]}}
 output['stages'][name]=stage
 output_path.write_text(json.dumps(output,ensure_ascii=False,indent=2))
 print('EVAL_STAGE_DONE',name,stage['metrics'],flush=True)
 del checkpoint;gc.collect();torch.cuda.empty_cache()
