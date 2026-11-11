#!/usr/bin/env python3
from worker import *
import hashlib
from loader_reference import load_model
rows=json.loads((R/'polysemy_probes.json').read_text());tok,model=load_model('Qwen3.8-27B-FP8');outputs={l:[]for l in range(64)};current={};tokens=[]
for l,block in enumerate(model.model.layers):
 def hook(m,i,o,l=l):
  h=o[0]if isinstance(o,tuple)else o;current[l]=h[0,-1].detach().float().cpu().numpy()
 block.register_forward_hook(hook)
with torch.inference_mode():
 for i,r in enumerate(rows):
  suffix=(' 'if r['lang']=='en'else'')+r['target'];assert r['text'].endswith(suffix);prefix=r['text'][:-len(suffix)];target_ids=tok.encode(suffix,add_special_tokens=False);ids=tok.encode(prefix,add_special_tokens=False)+target_ids;assert tok.decode(ids)==r['text'];tokens.append({'id':r['id'],'token_ids':ids,'last_token':tok.decode([ids[-1]]),'target_token_ids':target_ids,'matches_default_tokenization':ids==tok.encode(r['text'],add_special_tokens=False)})
  model.model(input_ids=torch.tensor([ids],device='cuda'),use_cache=False)
  for l in range(64):outputs[l].append(current[l].copy())
  current.clear();print('POLYSEMY',i+1,len(rows),'available_GiB',avail(),flush=True)
for l in range(64):
 a=np.stack(outputs[l]);assert a.shape==(72,5120)and np.isfinite(a).all();np.save(R/f'L{l:02d}'/'polysemy_probes.npy',a)
save(R/'polysemy_capture.json',{'records':72,'probes_sha256':hashlib.sha256((R/'polysemy_probes.json').read_bytes()).hexdigest(),'layers':list(range(64)),'dtype':'float32 from BF16 block outputs','tokenization':'prefix + canonical target suffix encoded separately, identical target token sequence within each language/lexeme; decoded text preserved','finite':True,'tokens':tokens,'time':time.time()})
