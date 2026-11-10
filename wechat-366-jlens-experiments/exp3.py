import torch,time,re
from interventions import operators,Edit,score,classify
@torch.inference_mode()
def run(c):
 start=time.time();l=38;prefix='对象：形状像一只靴子的欧洲国家。\n';pid=c.ids(prefix);anchor=len(pid)-1
 clean=c.capture(pid,True);ops=operators(c,'n100',[l],[[' Italy',' Japan'],['意大利','日本']]);V=ops[l]['both']['V'];B=ops[l]['both']['B'];h=clean[l][anchor:anchor+1];coords=h@V
 raw=(coords[:,[1,0,3,2]]-coords)@B.T
 queries=[('currency','这个国家的法定货币是','欧元','日元',['欧元','euro'],['日元','yen']),('capital','这个国家的首都是','罗马','东京',['罗马','rome'],['东京','tokyo']),('language','这个国家的官方语言是','意大利语','日语',['意大利语','italian'],['日语','japanese'])]
 out={'broadcast':[],'selectivity':[],'elapsed_seconds':None,'broadcast_definition':'One layer L38, one shared-prefix token; exact same additive delta across three separate downstream questions. Not a single forward producing three outputs.'}
 for name,suffix,old,new,oldaliases,newaliases in queries:
  ids=c.ids(prefix+suffix);assert ids[:len(pid)]==pid
  qclean=c.capture(ids,True);base=score(c,ids,old,new);gen=c.generate(ids,32)
  rec={'name':name,'prompt':prefix+suffix,'layer':l,'anchor_position':anchor,'shared_prefix_activation_max_abs_diff':float((qclean[l][anchor]-h[0]).abs().max()),'baseline':base,'baseline_generation':gen,'conditions':[]}
  for alpha in [.5,1.,2.]:
   delta=raw*alpha;delta*=min(1.,float(.25*h.norm()/delta.norm().clamp_min(1e-12)))
   for kind in ['swap','random']:
    d=delta if kind=='swap'else ops[l]['random'][None,:]*delta.norm(dim=-1,keepdim=True)
    ed=Edit(c,clean,ops,'both',alpha,len(ids),positions=[anchor],fixed_delta={l:d})
    res=score(c,ids,old,new,ed);res.update(kind=kind,alpha=alpha,perturbation=ed.stats)
    if alpha==1:
     with Edit(c,clean,ops,'both',alpha,len(ids),positions=[anchor],fixed_delta={l:d}):g=c.generate(ids,32)
     res['generation']=g;res['answer_class']=classify(g,oldaliases,newaliases)
    rec['conditions'].append(res)
  out['broadcast'].append(rec);c.save('experiment3.json',out);print('E3_BROADCAST',name,flush=True)
 # Same stimulus token IDs and exactly the same physical delta, two task contexts.
 stimulus='Le chat dort sur le canapé.';sid=c.ids(stimulus)
 tasks=[('continuation',sid,len(sid)-1),('name_language',c.ids('请用一个词说明这段文字的语种：\n')+sid+c.ids('\n答案：'),len(c.ids('请用一个词说明这段文字的语种：\n'))+len(sid)-1)]
 op=operators(c,'n100',[l],[[' French',' Spanish'],['法语','西班牙语']]);hc=c.capture(sid,True);v=op[l]['both']['V'];b=op[l]['both']['B'];h=hc[l][-1:];co=h@v;raw=(co[:,[1,0,3,2]]-co)@b.T
 for name,ids,anchor in tasks:
  base=score(c,ids,'法语','西班牙语');gen=c.generate(ids,48)
  rec={'task':name,'stimulus':stimulus,'token_ids':ids,'anchor_position':anchor,'layer':l,'baseline':base,'baseline_generation':gen,'conditions':[]}
  for alpha in [.5,1.,2.]:
   delta=raw*alpha;delta*=min(1.,float(.25*h.norm()/delta.norm().clamp_min(1e-12)))
   for kind in ['swap','random']:
    d=delta if kind=='swap'else op[l]['random'][None,:]*delta.norm(dim=-1,keepdim=True)
    ed=Edit(c,hc,op,'both',alpha,len(ids),positions=[anchor],fixed_delta={l:d});res=score(c,ids,'法语','西班牙语',ed);res.update(kind=kind,alpha=alpha)
    if alpha==1:
     with Edit(c,hc,op,'both',alpha,len(ids),positions=[anchor],fixed_delta={l:d}):g=c.generate(ids,48)
     res['generation']=g
    rec['conditions'].append(res)
  out['selectivity'].append(rec);c.save('experiment3.json',out);print('E3_SELECTIVITY',name,flush=True)
 out['elapsed_seconds']=time.time()-start;out['selectivity_definition']='Identical French stimulus token IDs, one L38 stimulus-final edit with same physical delta across raw continuation and Chinese explicit-language question. Language-name scores on continuation are diagnostics, not its task accuracy. Generated text retained for actual-language inspection.'
 c.save('experiment3.json',out)
