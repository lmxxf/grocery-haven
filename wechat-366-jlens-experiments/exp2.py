import torch,time,json
from interventions import operators,Edit,score,classify
CASES=[
 {'name':'boot_en','prompt':'Fact: The currency used in the country shaped like a boot is','pairs':[[' Italy',' Japan'],['意大利','日本']],'old':' euro','new':' yen','old_aliases':['euro','欧元'],'new_aliases':['yen','日元']},
 {'name':'boot_zh','prompt':'常识：形状像一只靴子的欧洲国家使用的法定货币是','pairs':[[' Italy',' Japan'],['意大利','日本']],'old':'欧元','new':'日元','old_aliases':['euro','欧元'],'new_aliases':['yen','日元']},
 {'name':'tokyo_zh','prompt':'常识：首都为东京的国家使用的货币是','pairs':[[' Japan',' Italy'],['日本','意大利']],'old':'日元','new':'欧元','old_aliases':['yen','日元'],'new_aliases':['euro','欧元']},
 {'name':'spider_en','prompt':'Fact: The number of legs on the animal that spins webs is','pairs':[[' spider',' ant'],['蜘蛛','蚂蚁']],'old':'8','new':'6','old_aliases':['8'],'new_aliases':['6'],'numeric':True},
 {'name':'spider_zh','prompt':'常识：会结网捕食飞虫的那种动物有几条腿？答案：','pairs':[[' spider',' ant'],['蜘蛛','蚂蚁']],'old':'8','new':'6','old_aliases':['8'],'new_aliases':['6'],'numeric':True},
 {'name':'arithmetic','prompt':'2*3+2=','pairs':[[' six',' ten'],['六','十']],'old':'8','new':'12','old_aliases':['8'],'new_aliases':['12'],'numeric':True}]
@torch.inference_mode()
def run(c):
 start=time.time();results=[]
 for case in CASES:
  ids=c.ids(case['prompt']);clean=c.capture(ids,True);layers=list(range(34,45));stage='n100';ops=operators(c,stage,layers,case['pairs'])
  base=score(c,ids,case['old'],case['new']);basegen=c.generate(ids,32)
  rec={'case':case,'stage':stage,'layers':layers,'scope':'all original prompt positions, prefill only; no generated-token edits','baseline':base,'baseline_generation':basegen,'conditions':[]}
  for group in ['english','chinese','both']:
   for alpha in [.5,1.,2.]:
    edit=Edit(c,clean,ops,group,alpha,len(ids))
    out=score(c,ids,case['old'],case['new'],edit);out.update(group=group,alpha=alpha,perturbation=edit.stats)
    if alpha==1:
     with Edit(c,clean,ops,group,alpha,len(ids)):gen=c.generate(ids,32)
     out['generation']=gen;out['answer_class']=classify(gen,case['old_aliases'],case['new_aliases'],case.get('numeric',False))
    out['new_first_token_logit_delta']=out['targets']['new']['first_token_logit']-base['targets']['new']['first_token_logit']
    rec['conditions'].append(out)
    random=Edit(c,clean,ops,'random',alpha,len(ids),matched=edit.norms)
    ctrl=score(c,ids,case['old'],case['new'],random);ctrl.update(group='random',matched_to=group,alpha=alpha,perturbation=random.stats)
    if group=='both'and alpha==1:
     with Edit(c,clean,ops,'random',alpha,len(ids),matched=edit.norms):gen=c.generate(ids,32)
     ctrl['generation']=gen;ctrl['answer_class']=classify(gen,case['old_aliases'],case['new_aliases'],case.get('numeric',False))
    ctrl['new_first_token_logit_delta']=ctrl['targets']['new']['first_token_logit']-base['targets']['new']['first_token_logit'];rec['conditions'].append(ctrl)
    print('E2_CONDITION',case['name'],group,alpha,flush=True)
  # Small calibration controls: same English boot swap using Vanilla and N=1 dictionaries.
  if case['name']=='boot_en':
   rec['calibration_controls']=[]
   for s in ['vanilla','n1']:
    op=operators(c,s,layers,case['pairs']);ed=Edit(c,clean,op,'both',1.,len(ids));out=score(c,ids,case['old'],case['new'],ed)
    with Edit(c,clean,op,'both',1.,len(ids)):gen=c.generate(ids,32)
    out.update(stage=s,generation=gen,answer_class=classify(gen,case['old_aliases'],case['new_aliases']));rec['calibration_controls'].append(out)
  results.append(rec);c.save('experiment2.json',{'results':results,'elapsed_seconds':time.time()-start,'method':'ridge-stabilized clean-coordinate clamp; V_l=J_l.T diag(final_norm.weight) W_U[token]; orthogonal complement unchanged, 25% residual L2 cap per location; random orthogonal to four named directions and matched to each semantic run actual per-position norm','generation_protocol':'greedy32, one per case/condition at alpha1; rates are case fractions, not sampling probabilities','number_swap':'6->10 uses English six/ten and Chinese 六/十 single-token labels; expected recomputed answer12. Numeric10/56 are not falsely treated as single vocabulary tokens.'})
