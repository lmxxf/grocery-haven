"""Bounded hook sanity check and strong single-pulse bread doses; no fishing loop."""
import torch,json
from interventions import Edit
@torch.inference_mode()
def run(c):
 e=json.loads((c.root/'experiment4.json').read_text());text=e['rendered_prompt'];ids=c.ids(text);l=38;anchor=len(ids)-1;clean=c.capture(ids,True);h=clean[l][-1:]
 v=c.dirs['n100'][l][' bread'];w=c.dirs['n100'][l]['面包'];u=v/v.norm()+w/w.norm();u=u/u.norm()
 gen=torch.Generator().manual_seed(20261110);r=torch.randn(5120,generator=gen);r-=u*(r@u);r/=r.norm()
 base=c.final(ids);result={'baseline_top1':c.tok.decode([int(base.argmax())]),'baseline_generation':e['baseline_generation'],'runs':[],'scope':'L38 final original prompt token only; same single-pulse scope as primary experiment; additional fixed doses0.5,1.0'}
 for alpha in [.1,.5,1.]:
  for kind,direction in [('bread',u),('random',r)]:
   delta=direction[None,:]*h.norm()*alpha
   ed=Edit(c,clean,{l:{}},'both',1,len(ids),positions=[anchor],fixed_delta={l:delta})
   with ed:changed=c.capture(ids,True)
   d38=float((changed[l][anchor]-clean[l][anchor]).norm()/h.norm());d39=float((changed[l+1][anchor]-clean[l+1][anchor]).norm()/h.norm())
   with Edit(c,clean,{l:{}},'both',1,len(ids),positions=[anchor],fixed_delta={l:delta}):z=c.final(ids)
   row={'kind':kind,'alpha':alpha,'observed_relative_change_L38':d38,'observed_relative_change_L39':d39,'next_logits_max_abs_change':float((z-base).abs().max()),'next_top1':c.tok.decode([int(z.argmax())])}
   if alpha in [.5,1.]:
    eg=Edit(c,clean,{l:{}},'both',1,len(ids),positions=[anchor],fixed_delta={l:delta})
    with eg:g=c.generate(ids,128)
    row['generation']=g;row['generation_hook_stats']=eg.stats;row['mentions_bread']=any(s in g['text'].lower()for s in ['bread','面包'])
   result['runs'].append(row);c.save('experiment4_dosecheck.json',result);print('E4_DOSECHECK',kind,alpha,d38,d39,flush=True)
