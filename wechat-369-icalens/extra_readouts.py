#!/usr/bin/env python3
# All models have exited before this script; a separate parent watchdog supervises it.
from worker import *
from safetensors import safe_open
from safetensors.torch import load_file
from transformers import AutoTokenizer
MODEL=Path('/home/lmxxf/work/models/Qwen3.8-27B-FP8')
tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True);vals={}
with safe_open(str(MODEL/'outside.safetensors'),framework='pt',device='cuda')as f:
 for key in ['lm_head.weight','model.language_model.norm.weight']:
  w=f.get_tensor(key)
  if w.dtype in [torch.float8_e4m3fn,torch.float8_e5m2]:
   sc=f.get_tensor(key+'_scale_inv');w=w.to(torch.bfloat16);w.view(w.shape[0]//128,128,w.shape[1]//128,128).mul_(sc[:,None,:,None].to(w.dtype))
  vals['head'if key=='lm_head.weight'else'norm']=w.float()
config=json.loads((MODEL/'config.json').read_text())['text_config'];eps=config['rms_norm_eps']
checkpoint=torch.load(R/'lens_n100.pt',map_location='cpu',mmap=True,weights_only=True)
rows=[json.loads(v)for v in (R/'corpus.jsonl').read_text().splitlines()if json.loads(v)['split']=='heldout'];ends=np.cumsum([len(v['token_ids'])for v in rows])
for l in range(64):
 p=R/f'L{l:02d}';t=load_file(str(p/'oriented.safetensors'),device='cuda');M=t['mixing'];poly=json.loads((p/'polysemy_analysis.json').read_text());stats=json.loads((p/'statistics.json').read_text());axes=poly['extra_axes'];J=None if l==63 else checkpoint['J'][l].float().cuda();out={}
 for start in range(0,len(axes),8):
  ix=axes[start:start+8]
  for sign in [1,-1]:
   d=sign*M[:,ix].T
   for name,y in [('vanilla',d),('jlens_n100',d if J is None else d@J.T)]:
    y=y*torch.rsqrt(y.square().mean(-1,keepdim=True)+eps)*(1+vals['norm']);logits=y@vals['head'].T;assert torch.isfinite(logits).all();v,indices=logits.topk(20,dim=-1)
    for axis,ids,vs in zip(ix,indices.cpu().tolist(),v.cpu().tolist()):out.setdefault(str(axis),{}).setdefault('positive'if sign==1 else'negative',{})[name]=[{'token_id':ti,'text':tok.decode([ti]),'logit':vi}for ti,vi in zip(ids,vs)]
 save(p/'polysemy_readouts.json',{'layer':l,'axes':out,'alignment':f'signed writing direction -> J_l or identity -> Qwen RMSNorm(1+weight,eps={eps}) -> lm_head; wordpiece ranking not concept proof'})
 # Decode the entire token slice in one call; individual byte-BPE token decoding can corrupt Chinese.
 contexts={}
 for axis in sorted(set(axes+stats['selected_candidate_axes'])):
  contexts[axis]=[]
  for rank in range(5):
   ix=stats['top_heldout']['indices'][rank][axis];ri=int(np.searchsorted(ends,ix,side='right'));off=ix-(int(ends[ri-1])if ri else 0);r=rows[ri];ids=r['token_ids'][max(0,off-64):off+1];contexts[axis].append({'activation':stats['top_heldout']['values'][rank][axis],'source_lang':r['lang'],'left_context':tok.decode(ids),'document_id':r['document_id'],'heldout_flat_token_index':ix,'position_in_window':off})
 save(p/'contexts_decoded.json',{'layer':l,'decode_policy':'entire causal left token slice in one decode, never future tokens','axes':contexts});print('EXTRA_READOUTS',l,flush=True)
 del t,M,J;gc.collect();torch.cuda.empty_cache()
save(R/'extra_readouts_complete.json',{'layers':64,'finite_logits':True,'norm_eps':eps,'time':time.time()})
