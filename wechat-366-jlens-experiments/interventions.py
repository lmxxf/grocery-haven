"""Clean-coordinate clamped swaps with per-location matched random controls.
All edits are on block outputs. No gradients, model-weight changes or J inverse.
"""
import torch,math,re,contextlib

def operators(c,stage,layers,pairs):
 out={}
 for l in layers:
  full=torch.stack([c.dirs[stage][l][s]for pair in pairs for s in pair],dim=1).double()
  Q,_=torch.linalg.qr(full,mode='reduced')
  gen=torch.Generator().manual_seed(20261110+l)
  r=torch.randn(c.lm.d_model,generator=gen,dtype=torch.float64);r=r-Q@(Q.T@r);r=r/r.norm()
  row={'random':r.float()}
  for group,indices in [('english',[0,1]),('chinese',[2,3]),('both',[0,1,2,3])]:
   V=full[:,indices];G=V.T@V;ridge=1e-6*G.diag().mean();B=V@torch.linalg.inv(G+ridge*torch.eye(len(indices),dtype=torch.float64))
   row[group]={'V':V.float(),'B':B.float(),'condition_number':float(torch.linalg.cond(G)),'ridge':float(ridge)}
  out[l]=row
 return out

class Edit:
 def __init__(self,c,clean,ops,group,alpha,prompt_len,positions=None,matched=None,fixed_delta=None):
  self.c=c;self.clean=clean;self.ops=ops;self.group=group;self.alpha=alpha;self.prompt_len=prompt_len;self.positions=positions if positions is not None else list(range(prompt_len));self.matched=matched;self.fixed_delta=fixed_delta;self.norms={};self.stats={};self.handles=[]
 def hook(self,l):
  def fn(mod,args,out):
   x=out if torch.is_tensor(out)else out[0]
   if x.shape[1]<self.prompt_len:return
   pos=self.positions;h=x[0,pos].float()
   if self.fixed_delta is not None:delta=self.fixed_delta[l].to(h.device)
   elif self.group=='random':
    delta=self.ops[l]['random'].to(h.device)[None,:]*self.matched[l].to(h.device)[:,None]
   else:
    op=self.ops[l][self.group];V=op['V'].to(h.device);B=op['B'].to(h.device)
    clean=self.clean[l][pos].to(h.device);coords=clean@V
    perm=[1,0]if V.shape[1]==2 else [1,0,3,2]
    target=coords+self.alpha*(coords[:,perm]-coords)
    delta=(target-h@V)@B.T
    cap=.25*clean.norm(dim=-1,keepdim=True);scale=torch.minimum(torch.ones_like(cap),cap/delta.norm(dim=-1,keepdim=True).clamp_min(1e-12));delta*=scale
   edited=(h+delta).to(x.dtype);actual=edited.float()-h
   if l not in self.norms:
    self.norms[l]=actual.norm(dim=-1).cpu();self.stats[l]={'mean_relative_L2':float((actual.norm(dim=-1)/h.norm(dim=-1).clamp_min(1e-9)).mean()),'max_relative_L2':float((actual.norm(dim=-1)/h.norm(dim=-1).clamp_min(1e-9)).max())}
   y=x.clone();y[0,pos]=edited
   return y if torch.is_tensor(out)else(y,*out[1:])
  return fn
 def __enter__(self):
  for l in self.ops:self.handles.append(self.c.lm.layers[l].register_forward_hook(self.hook(l)))
  return self
 def __exit__(self,*args):
  for h in self.handles:h.remove()

def rank(z,i):return 1+int((z>z[i]).sum())
@torch.inference_mode()
def score(c,ids,old,new,edit=None):
 with edit if edit else contextlib.nullcontext():
  z=c.final(ids);logp=z-z.logsumexp(0);probs=z.softmax(0)
  vals,inds=z.topk(5);out={'top5':[{'id':int(i),'text':c.tok.decode([int(i)]),'logit':float(v)}for i,v in zip(inds,vals)],'entropy_nats':float(-(probs*logp).sum()),'targets':{}}
  for label,text in [('old',old),('new',new)]:
   target=c.ids(text);lp=float(logp[target[0]])
   if len(target)>1:
    full=c.model(torch.tensor([ids+target[:-1]],device='cuda'),use_cache=False).logits[0].float()
    lp=sum(float(full[len(ids)-1+j,t]-full[len(ids)-1+j].logsumexp(0))for j,t in enumerate(target))
   out['targets'][label]={'text':text,'token_ids':target,'sequence_logprob':lp,'mean_logprob_per_token':lp/len(target),'first_token_logit':float(z[target[0]]),'first_token_rank':rank(z,target[0]),'whole_string_vocabulary_rank':rank(z,target[0])if len(target)==1 else None}
  out['new_minus_old_sequence_logprob']=out['targets']['new']['sequence_logprob']-out['targets']['old']['sequence_logprob']
 return out

def classify(gen,old_aliases,new_aliases,numeric=False):
 s=gen['text'].strip().split('\n')[0].lower()
 if numeric:
  m=re.search(r'[-+]?\d+',s);answer=m.group(0)if m else None
  return {'first_answer':answer,'new_answer':answer in new_aliases if answer else False,'old_answer':answer in old_aliases if answer else False}
 a=any(w.lower()in s for w in old_aliases);b=any(w.lower()in s for w in new_aliases)
 return {'first_answer':s,'new_answer':b and not a,'old_answer':a and not b,'mixed_or_unclear':a==b}
