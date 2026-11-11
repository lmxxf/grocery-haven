#!/usr/bin/env python3
# Imports guard before torch/model allocations.
from worker import *
from safetensors import safe_open
from safetensors.torch import load_file
from transformers import AutoTokenizer
MODEL=Path('/home/lmxxf/work/models/Qwen3.8-27B-FP8')
def readout(l):
 p=R/f'L{l:02d}';t=load_file(str(p/'oriented.safetensors'),device='cuda');M=t['mixing'];meta=json.loads((p/'statistics.json').read_text());axes=meta['selected_candidate_axes'];tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
 vals={}
 for shard in ['outside.safetensors','layers-63.safetensors']:
  with safe_open(str(MODEL/shard),framework='pt',device='cuda')as f:
   for k in f.keys():
    if k.endswith('lm_head.weight')or k in ['model.language_model.norm.weight','model.norm.weight']:
     w=f.get_tensor(k)
     if w.dtype in [torch.float8_e4m3fn,torch.float8_e5m2]:
      sc=f.get_tensor(k+'_scale_inv');w=w.to(torch.bfloat16);w.view(w.shape[0]//128,128,w.shape[1]//128,128).mul_(sc[:,None,:,None].to(w.dtype))
     vals['head'if 'lm_head'in k else'norm']=w.float()
 assert set(vals)=={'head','norm'},vals.keys()
 J=None if l==63 else torch.load(R/'lens_n100.pt',map_location='cpu',mmap=True,weights_only=True)['J'][l].float().cuda()
 out={}
 for start in range(0,len(axes),8):
  ix=axes[start:start+8];dirs=M[:,ix].T
  for name,y in [('vanilla',dirs),('jlens_n100',dirs if J is None else dirs@J.T)]:
   y=y*torch.rsqrt(y.square().mean(-1,keepdim=True)+1e-6)*(1.0+vals['norm']);logits=y@vals['head'].T;v,i=logits.topk(20,dim=-1)
   for j,ids,vs in zip(ix,i.cpu().tolist(),v.cpu().tolist()):out.setdefault(str(j),{})[name]=[{'token_id':ti,'text':tok.decode([ti]),'logit':vi}for ti,vi in zip(ids,vs)]
 save(p/'vocabulary_readouts.json',{'layer':l,'alignment':'oriented writing direction -> J_l (identity L63) -> Qwen3.5 final RMSNorm(1+weight,eps=1e-6) -> lm_head; directional word probe, not causal proof','axes':out})
 print('READOUT_COMPLETE',l,flush=True)
def steer(l):
 from loader_reference import load_model
 p=R/f'L{l:02d}';t=load_file(str(p/'oriented.safetensors'),device='cuda');axis=json.loads((p/'statistics.json').read_text())['language_axis'];C=t['components'][axis];M=t['mixing'][:,axis];c=t['center'];tok,model=load_model('Qwen3.8-27B-FP8');runs=[]
 prompts=['Hangzhou is known for','杭州以什么闻名？'];mode={'kind':'baseline'}
 def hook(mod,inp,out):
  if mode['kind']=='baseline':return out
  h=out[0]if isinstance(out,tuple)else out;h=h.clone();v=h[:,-1,:].float();norm=v.norm(dim=-1,keepdim=True);x=v/norm.clamp_min(1e-12);before=((x-c)*C).sum(-1,keepdim=True);delta=-before if mode['kind']=='clamp'else torch.full_like(before,mode['dose']);x=x+delta*M;x=x/x.norm(dim=-1,keepdim=True).clamp_min(1e-12);h[:,-1,:]=(x*norm).to(h.dtype)
  return (h,*out[1:])if isinstance(out,tuple)else h
 handle=model.model.layers[l].register_forward_hook(hook)
 with torch.inference_mode():
  for prompt in prompts:
   for kind,dose in [('baseline',0),('steer',-5),('steer',5),('clamp',0)]:
    mode.update(kind=kind,dose=dose);ids=tok(prompt,return_tensors='pt').to('cuda');n=ids.input_ids.shape[1];y=model.generate(**ids,max_new_tokens=32,do_sample=False,use_cache=True,pad_token_id=tok.eos_token_id);runs.append({'prompt':prompt,'kind':kind,'coordinate_delta':dose,'generated':tok.decode(y[0,n:],skip_special_tokens=False)})
 handle.remove();save(p/'steering.json',{'layer':l,'axis':axis,'scope':'prompt last position and every decode last position','method':'unit-row coordinate edit then unit renormalization and original norm restoration; clamp coordinate before renormalization','runs':runs});print('STEERING_COMPLETE',l,flush=True)
if __name__=='__main__':
 mode=sys.argv[1];l=int(sys.argv[2]);readout(l)if mode=='readout'else steer(l)
