import torch,re,time
from interventions import Edit
@torch.inference_mode()
def run(c):
 start=time.time();l=38
 prompt='今天下午我想先散步，再整理书桌。请给个简短安排。如果回答时察觉某个与任务无关、突然冒出的具体概念，可以顺带说出来；没有就不用补充。请在80字以内回答。'
 text=c.tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
 ids=c.ids(text);clean=c.capture(ids,True);anchor=len(ids)-1;h=clean[l][-1:];scale=float(h.norm())
 def direction(stage,keys):
  a=[c.dirs[stage][l][k]/c.dirs[stage][l][k].norm()for k in keys];v=sum(a);return v/v.norm()
 concepts=[('bread',[' bread','面包'],['bread','面包']),('hotpot',['火锅'],['火锅','hotpot','hot pot']),('elephant',['大象'],['大象','elephant'])]
 vectors={name:direction('n100',keys)for name,keys,aliases in concepts};V=torch.stack(list(vectors.values()),1).double();Q,_=torch.linalg.qr(V,mode='reduced');g=torch.Generator().manual_seed(20261110);r=torch.randn(5120,generator=g,dtype=torch.float64);r-=Q@(Q.T@r);r=(r/r.norm()).float()
 def analyze(gen,aliases):
  s=gen['text'];named=any(a.lower()in s.lower()for a in aliases);flags=['注意到','察觉','脑海','脑子','浮现','突然想到','联想','无关','冒出']
  toks=gen['token_ids'];grams=[tuple(toks[i:i+4])for i in range(max(0,len(toks)-3))];repetition=1-len(set(grams))/len(grams)if grams else 0
  return {'named_concept':named,'elicited_self_report_phrase':named and any(p in s for p in flags),'repeated_4gram_fraction':repetition,'degenerate_repeat_flag':repetition>.3,'hit_limit':gen['hit_limit']}
 baseline=c.generate(ids,128)
 result={'prompt':prompt,'rendered_prompt':text,'layer':l,'position':anchor,'baseline_generation':baseline,'runs':[],'method':'single L38 final-prompt-position additive injection, delta=alpha*clean_residual_L2*unit_concept_direction; prompt names no target; semantic-report request is explicit, so not unprompted introspection or consciousness evidence'}
 for name,keys,aliases in concepts:
  for alpha in [.05,.1,.2]:
   delta=vectors[name][None,:]*scale*alpha
   with Edit(c,clean,{l:{}},'both',1.,len(ids),positions=[anchor],fixed_delta={l:delta}):gen=c.generate(ids,128)
   result['runs'].append({'concept':name,'stage':'n100','kind':'concept','alpha':alpha,'generation':gen,'analysis':analyze(gen,aliases)})
   c.save('experiment4.json',result);print('E4',name,alpha,flush=True)
 for alpha in [.05,.1,.2]:
  with Edit(c,clean,{l:{}},'both',1.,len(ids),positions=[anchor],fixed_delta={l:r[None,:]*scale*alpha}):gen=c.generate(ids,128)
  result['runs'].append({'concept':'all_targets','stage':'n100','kind':'random','alpha':alpha,'generation':gen,'analysis':analyze(gen,[a for _,_,aliases in concepts for a in aliases])});c.save('experiment4.json',result)
 for stage in ['n1','vanilla']:
  v=direction(stage,[' bread','面包'])
  with Edit(c,clean,{l:{}},'both',1.,len(ids),positions=[anchor],fixed_delta={l:v[None,:]*scale*.1}):gen=c.generate(ids,128)
  result['runs'].append({'concept':'bread','stage':stage,'kind':'calibration_control','alpha':.1,'generation':gen,'analysis':analyze(gen,['bread','面包'])});c.save('experiment4.json',result)
 result['elapsed_seconds']=time.time()-start;c.save('experiment4.json',result)
