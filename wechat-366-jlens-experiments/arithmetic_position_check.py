"""Exploratory localization follow-up prompted by Exp1's actual L55+ peak."""
import torch,time
from interventions import operators,Edit,score,classify
@torch.inference_mode()
def run(c):
 ids=c.ids('2*3+2=');clean=c.capture(ids,True);norm=c.model.model.norm.weight.float();keys=['6','4','六','四'];W=torch.stack([c.model.lm_head.weight[c.single(s)].float()*norm for s in keys])
 for l in range(54,59):
  J=c.checkpoints[100]['J'][l].to('cuda',dtype=torch.float32);V=W@J
  for s,v in zip(keys,V):c.dirs['n100'][l][s]=v.cpu()
  del J
 base=score(c,ids,'8','6');bg=c.generate(ids,24)
 out={'prompt':'2*3+2=','definition':'6->4 numeric English-digit directions and 六->四 Chinese directions; expected answer4+2=6; exploratory follow-up after observing peak around L55-56, not a preregistered independent confirmation','baseline':base,'baseline_generation':bg,'runs':[]}
 setups=[('single_operand',[56],[2]),('single_plus',[56],[3]),('single_last',[56],[5]),('band_early_nodes',list(range(54,59)),[2,3]),('band_last',list(range(54,59)),[5]),('band_all',list(range(54,59)),list(range(len(ids))))]
 for name,layers,positions in setups:
  ops=operators(c,'n100',layers,[['6','4'],['六','四']])
  for alpha in [1.,2.]:
   ed=Edit(c,clean,ops,'both',alpha,len(ids),positions=positions);res=score(c,ids,'8','6',ed)
   res.update(name=name,kind='semantic',layers=layers,positions=positions,alpha=alpha,perturbation=ed.stats)
   if alpha==1:
    with Edit(c,clean,ops,'both',alpha,len(ids),positions=positions):gen=c.generate(ids,24)
    res['generation']=gen;res['answer_class']=classify(gen,['8'],['6'],True)
   out['runs'].append(res)
   rd=Edit(c,clean,ops,'random',alpha,len(ids),positions=positions,matched=ed.norms);ctrl=score(c,ids,'8','6',rd)
   ctrl.update(name=name,kind='random',layers=layers,positions=positions,alpha=alpha,perturbation=rd.stats)
   if alpha==1:
    with Edit(c,clean,ops,'random',alpha,len(ids),positions=positions,matched=ed.norms):gen=c.generate(ids,24)
    ctrl['generation']=gen;ctrl['answer_class']=classify(gen,['8'],['6'],True)
   out['runs'].append(ctrl);c.save('arithmetic_position_check.json',out)
  print('ARITHMETIC_PATCH',name,flush=True)
