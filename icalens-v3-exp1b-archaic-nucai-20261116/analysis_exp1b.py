import os,sys,json,time,gzip,gc,hashlib,re
from pathlib import Path
import numpy as np
from scipy.stats import t as student,ttest_ind,ttest_rel
R=Path(__file__).resolve().parent;V3=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3');ASSET=V3/'hf_clean_upload';H=V3/'experiments/exp1b_archaic_nucai'
GROUPS=['Mod_Moral_Beibi','Moral_Nonliteral','Status_Humble','R1_Humiliation','R2_Court'];WRAPS=['short','W2_native','W2_shared','W3'];COHORTS=['A1','A2','B','C','B_imperial','A1_translation_audit']
def read(p):return json.loads(Path(p).read_text())
def save(name,data,heavy=False):
 text=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False);p=(H if heavy or len(text.encode())>10_000_000 else R)/name;p.write_text(text);return str(p)
def bh(p):
 ix=np.argsort(p);q=np.empty_like(p);q[ix]=np.minimum(1,np.minimum.accumulate((p[ix]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]);return q
def paired_vectors(z,ps):
 a=z[[p['a'] for p in ps]].astype('float64');b=z[[p['b'] for p in ps]].astype('float64');d=a-b;n=len(d);mu=d.mean(0);sd=d.std(0,ddof=1);dz=np.divide(mu,sd,out=np.zeros_like(mu),where=sd>1e-12);pooled=np.sqrt((a.var(0,ddof=1)+b.var(0,ddof=1))/2);cohen=np.divide(mu,pooled,out=np.zeros_like(mu),where=pooled>1e-12)
 return dict(a=a,b=b,diff=d,mean=mu,dz=dz,t=dz*np.sqrt(n),d=cohen,n=n)
def metric(st,c,sign):
 df=st['diff'][:,c]*sign;return dict(n=len(df),correct=int((df>0).sum()),delta=float(st['mean'][c]*sign),raw_delta=float(st['mean'][c]),d=float(st['d'][c]*sign),dz=float(st['dz'][c]*sign),t=float(st['t'][c]*sign),p=float(2*student.sf(abs(st['t'][c]),len(df)-1)),differences=df.tolist())
def cluster_summary(values,docs):
 values=np.asarray(values,dtype='float64');unique=sorted(set(docs));sums=np.array([values[np.array(docs)==d].sum() for d in unique]);ns=np.array([docs.count(d) for d in unique]);means=sums/ns
 rng=np.random.default_rng(20261116);indices=rng.integers(0,len(unique),(1000,len(unique)));boot=sums[indices].sum(1)/ns[indices].sum(1);low,high=np.quantile(boot,[.025,.975])
 return dict(n=len(values),documents=len(unique),mean=float(values.mean()),sd=float(values.std(ddof=1)) if len(values)>1 else 0.,ci95=[float(low),float(high)],positive=int((values>0).sum()),values=values.tolist(),document_means=dict(zip(unique,means.tolist())))
def cohort_indices(samples,group,wrapper,target='奴才',split=None):return [s['id'] for s in samples if s['group']==group and s['wrapper']==wrapper and s['target']==target and (split is None or s['split']==split)]
def cohort_details(z,zm,samples,c,sign,scale):
 result={}
 for w in WRAPS:
  result[w]={}
  for group in COHORTS:
   ss=[s for s in samples if s['group']==group and s['wrapper']==w and s['target']=='奴才']
   if not ss:continue
   ids=[s['id'] for s in ss];docs=[s['doc_id'] for s in ss];values=z[ids,c]*sign;record={'raw':cluster_summary(values,docs),'mean_token_raw':cluster_summary(zm[ids,c]*sign,docs),'minimal_pairs':{}}
   for target in ['臣'] if group=='A1' else ['小的','下官','我'] if group=='A2' else []:
    alt={s['sample_id']:s['id'] for s in samples if s['group']==group and s['wrapper']==w and s['target']==target};other=[alt[s['sample_id']] for s in ss];dif=(z[ids,c]-z[other,c])*sign;mdif=(zm[ids,c]-zm[other,c])*sign;summary=cluster_summary(dif,docs);summary['modern_scale']=float(scale);summary['normalized_mean']=float(np.mean(dif)/scale) if abs(scale)>1e-8 else None;summary['normalized_ci95']=[float(v/scale) for v in summary['ci95']] if scale>1e-8 else None
    summary['equivalent_within_10pct_modern_gap']=bool(scale>1e-8 and max(abs(v) for v in summary['ci95'])<=.1*scale);summary['mean_token']=cluster_summary(mdif,docs);summary['paired_t_p']=float(ttest_rel(z[ids,c].astype('float64'),z[other,c].astype('float64')).pvalue) if len(ids)>1 and np.std(dif)>0 else None
    record['minimal_pairs'][target]=summary
   result[w][group]=record
 return result

def calibration(z,zm,cal,c,sign,modgap):
 groups={w:{s['target']:s['id'] for s in cal if s['wrapper']==w} for w in ['W0','W1','W2','W3a','W3b']};d0=(z[groups['W0']['卑鄙'],c]-np.mean([z[groups['W0'][t],c] for t in ['微贱','浅陋','愚钝']]))*sign;result={}
 for w,ids in groups.items():
  val=float(z[ids['卑鄙'],c]*sign);neutrals={t:float(z[ids[t],c]*sign) for t in ['微贱','浅陋','愚钝']};delta=val-np.mean(list(neutrals.values()));ratio=delta/modgap if abs(modgap)>1e-8 else None;rel=1-delta/d0 if abs(d0)>1e-6 else None
  mv=float((zm[ids['卑鄙'],c]-np.mean([zm[ids[t],c] for t in neutrals]))*sign)
  result[w]=dict(raw_beibi=val,raw_neutrals=neutrals,matched_delta=float(delta),modern_gap=float(modgap),normalized_modern_gap=None if ratio is None else float(ratio),removal_percent_modern_anchor=None if ratio is None else float(100*(1-ratio)),removal_percent_vs_W0=None if rel is None else float(100*rel),mean_token_matched_delta=mv)
 return result

def layer_analysis(z,zm,pairs,samples,cal,kurt,l):
 out={'layer':l,'references':{},'internal':{}}
 ref={g:paired_vectors(z,[p for p in pairs if p['group']==g and p['split']=='fit']) for g in GROUPS};mref={g:paired_vectors(zm,[p for p in pairs if p['group']==g and p['split']=='fit']) for g in GROUPS}
 for g,st in ref.items():
  out['references'][g]={}
  held=[p for p in pairs if p['group']==g and p['split']=='heldout'];heldstats=paired_vectors(z,held) if held else None
  q=bh(2*student.sf(np.abs(st['t']),st['n']-1))
  for method,crit in [('delta',np.abs(st['mean'])),('t',np.abs(st['t']))]:
   c=int(crit.argmax());sgn=float(np.sign(st['mean'][c]) or 1);modgap=float(ref['Mod_Moral_Beibi']['mean'][c]*sgn);v=dict(axis=c,sign=sgn,kurtosis=float(kurt[c]),fit=metric(st,c,sgn),fit_q_BH_5120=float(q[c]),heldout=None if heldstats is None else metric(heldstats,c,sgn),beibi_transfer=metric(ref['Mod_Moral_Beibi'],c,sgn),mean_token_top1=int(np.abs(mref[g]['mean' if method=='delta' else 't']).argmax()),calibration=calibration(z,zm,cal,c,sgn,modgap),cohorts=cohort_details(z,zm,samples,c,sgn,float(st['mean'][c]*sgn)))
   out['references'][g][method]=v
 # Same target word, independent planned discovery contrasts. All selections use fit documents only.
 contrasts={'court_vs_modern':(['A1'],['C']),'domestic_vs_modern':(['A2'],['C']),'insult_vs_routine_HLM':(['B'],['A2'])}
 for name,(positive,negative) in contrasts.items():
  ix=lambda gs,split:[s['id'] for s in samples if s['group'] in gs and s['wrapper']=='W2_native' and s['target']=='奴才' and s['split']==split]
  a=ix(positive,'fit');b=ix(negative,'fit');assert a and b,(name,a,b)
  x=z[a].astype('float64');y=z[b].astype('float64');delta=x.mean(0)-y.mean(0);var=x.var(0,ddof=1)/len(a)+y.var(0,ddof=1)/len(b);t=delta/np.maximum(var,1e-12)**.5
  selected=[]
  for c0 in np.argsort(-np.abs(delta))[:3]:
   c=int(c0);sign=float(np.sign(delta[c]) or 1);threshold=float((x[:,c].mean()+y[:,c].mean())/2);cases=[]
   for gset,label in [(positive,1),(negative,-1)]:
    for i in ix(gset,'heldout'):cases.append(dict(id=i,label=label,score=float(z[i,c]),correct=bool((z[i,c]-threshold)*sign*label>0)))
   selected.append(dict(axis=c,sign=sign,kurtosis=float(kurt[c]),fit_delta=float(delta[c]*sign),fit_t=float(t[c]*sign),fit_n=[len(a),len(b)],heldout_correct=sum(v['correct'] for v in cases),heldout_total=len(cases),heldout_cases=cases,group_means={g:float(np.mean(z[cohort_indices(samples,g,'W2_native'),c])*sign) for g in ['A1','A2','B','C']}))
  out['internal'][name]={'top3_delta':selected,'top1_t':int(np.abs(t).argmax())}
 return out

def choose_representatives(results):
 reps=[]
 for group in ['Moral_Nonliteral','R1_Humiliation','R2_Court']:
  for band in [(10,20),(24,48)]:
   rows=[r for r in results if band[0]<=r['layer']<=band[1]]
   def rank(r):
    v=r['references'][group]['delta'];return (v['heldout']['correct']/v['heldout']['n'],v['heldout']['d'],abs(v['fit']['delta'])) if v['heldout'] else (abs(v['fit']['d']),abs(v['fit']['delta']))
   r=max(rows,key=rank);v=r['references'][group]['delta'];reps.append(dict(layer=r['layer'],axis=v['axis'],sign=v['sign'],name=group,method='delta',band=list(band)))
 r=max(results[10:49],key=lambda r:r['references']['Status_Humble']['delta']['fit']['d']);v=r['references']['Status_Humble']['delta'];reps.append(dict(layer=r['layer'],axis=v['axis'],sign=v['sign'],name='Status_Humble',method='delta'))
 for name in ['court_vs_modern','insult_vs_routine_HLM']:
  r=max(results[20:49],key=lambda r:(r['internal'][name]['top3_delta'][0]['heldout_correct']/max(1,r['internal'][name]['top3_delta'][0]['heldout_total']),r['internal'][name]['top3_delta'][0]['fit_delta']));v=r['internal'][name]['top3_delta'][0];reps.append(dict(layer=r['layer'],axis=v['axis'],sign=v['sign'],name=name,method='internal'))
 return reps

def readouts(model,tok,reps,manifest):
 import torch
 from safetensors.torch import load_file
 archive=torch.load(V3/'readouts/lens_n100.pt',map_location='cpu',weights_only=True,mmap=True);out=[];cache={}
 for rep in reps:
  l=rep['layer'];c=rep['axis'];key=(l,c)
  if key in cache:out.append(dict(**rep,**cache[key]));continue
  asset=load_file(str(ASSET/manifest['layers'][str(l)]['file']));writing=asset['writing_matrix'][:,c].float().cuda();mapping=archive['J'].get(l,archive['J'].get(str(l)))
  with torch.inference_mode():
   mapped=mapping.float().cuda()@writing;h=model.model.norm(mapped.to(torch.bfloat16)[None,None,:]);scores=model.lm_head(h)[0,0].float().cpu().numpy()
  def entry(i):return dict(token_id=int(i),token=tok.convert_ids_to_tokens(int(i)),text=tok.decode([int(i)]),score=float(scores[i]))
  profile=json.loads(gzip.decompress((ASSET/manifest['layers'][str(l)]['component_profile']).read_bytes()))['components'][c];old=profile['additional_readouts']['J Lens']['positive']['top_tokens'];error=max(abs(float(scores[e['token_id']])-e['logit']) for e in old)
  data=dict(positive_top25=[entry(i) for i in np.argsort(-scores)[:25]],negative_top25=[entry(i) for i in np.argsort(scores)[:25]],profile=profile,stored_top20_max_score_error=error);cache[key]=data;out.append(dict(**rep,**data));del asset,writing,mapping,profile;gc.collect();print('READOUT',rep['name'],l,c,flush=True)
 return out

def repair_navigation(model,tok,probes):
 import torch
 nav='上一回\n回目录\n下一回\n';todo=[p for p in probes if nav in p['text']]
 if not todo:return
 last=np.load(H/'activations_last.npy',mmap_mode='r+');mean=np.load(H/'activations_mean.npy',mmap_mode='r+');cur=[0,0];handles=[]
 for l,block in enumerate(model.model.layers):
  def hook(m,i,o,l=l):
   h=(o[0] if isinstance(o,tuple) else o)[0];j,k=cur;last[l,j]=h[-1].float().cpu().numpy();mean[l,j]=h[k:].float().mean(0).cpu().numpy()
  handles.append(block.register_forward_hook(hook))
 audit=[]
 with torch.inference_mode():
  for p in todo:
   before=p['text'];p['text']=before.replace(nav,'');prefix=p['text'][:-len(p['target'])];ids=tok.encode(prefix,add_special_tokens=False)+p['target_ids'];assert tok.decode(ids)==p['text'];p['input_ids']=ids;p['target_start']=len(ids)-len(p['target_ids']);p['token_count']=len(ids);cur[:]=[p['id'],p['target_start']];model.model(input_ids=torch.tensor([ids],device='cuda'),use_cache=False);audit.append(dict(id=p['id'],removed=nav,old_chars=len(before),new_chars=len(p['text'])))
 for handle in handles:handle.remove()
 last.flush();mean.flush();save('navigation_cleanup.json',audit);save('probes.json',probes);print('NAVIGATION_CLEANED',len(todo),flush=True)

def run(model,tok):
 import torch
 from safetensors.torch import load_file
 torch.set_num_threads(8);torch.set_float32_matmul_precision('highest');start=time.time();probes=read(R/'probes.json');pairs=read(R/'pairs.json');samples=read(R/'samples.json');cal=read(R/'calibration_design.json')['calibration'];manifest=read(ASSET/'icalens.json')
 repair_navigation(model,tok,probes)
 n=len(probes);last=np.load(H/'activations_last.npy',mmap_mode='r');mean=np.load(H/'activations_mean.npy',mmap_mode='r');z=np.lib.format.open_memmap(H/'z_last.npy',mode='w+',dtype='float32',shape=(64,n,5120));zm=np.lib.format.open_memmap(H/'z_mean.npy',mode='w+',dtype='float32',shape=(64,n,5120));results=[];checks=[]
 for l in range(64):
  asset=load_file(str(ASSET/manifest['layers'][str(l)]['file']),device='cuda');C=asset['reading_matrix'];center=asset['center']
  for source,out in [(last,z),(mean,zm)]:
   x=torch.tensor(np.array(source[l]),device='cuda');out[l]=((x/x.norm(dim=1,keepdim=True).clamp_min(1e-12)-center)@C.T).cpu().numpy()
  if l in [0,16,32,48,63]:
   raw=np.array(last[l,:2]);cpu=(raw/np.linalg.norm(raw,axis=1,keepdims=True)-center.cpu().numpy())@C.cpu().numpy().T;err=float(np.max(np.abs(cpu-z[l,:2])));checks.append(dict(layer=l,cpu_gpu_projection_max_abs_error=err));assert err<1e-3
  kurt=read(V3/f'L{l:02d}/statistics.json')['test']['excess_kurtosis'];results.append(layer_analysis(z[l],zm[l],pairs,samples,cal,kurt,l));print('ANALYZED',l,flush=True);save('progress.json',dict(stage='analysis',done=l+1,total=64));del asset,C,center,x;gc.collect()
 z.flush();zm.flush();fullpath=save('all_layers_full.json',results,heavy=True)
 # Compact archive copy contains every layer's axis IDs and principal numbers; large detail remains local.
 compact=[]
 for r in results:
  item={'layer':r['layer'],'references':{},'internal':r['internal']}
  for g,methods in r['references'].items():
   item['references'][g]={}
   for method,v in methods.items():
    item['references'][g][method]={k:value for k,value in v.items() if k!='cohorts'}
    item['references'][g][method]['cohorts']={w:{co:dict(mean=d['raw']['mean'],ci95=d['raw']['ci95'],n=d['raw']['n'],minimal_pairs={t:{k:x[k] for k in ['mean','ci95','normalized_mean','equivalent_within_10pct_modern_gap']} for t,x in d['minimal_pairs'].items()}) for co,d in groups.items()} for w,groups in v['cohorts'].items()}
  compact.append(item)
 compactpath=save('layers_summary.json',compact);reps=choose_representatives(results);save('representatives.json',reps);rd=readouts(model,tok,reps,manifest)
 # Exact geometry for planned court and insult axes, without equating different ICA IDs to Euclidean orthogonality.
 geometry=[]
 for l in range(64):
  c1=results[l]['internal']['court_vs_modern']['top3_delta'][0]['axis'];c2=results[l]['internal']['insult_vs_routine_HLM']['top3_delta'][0]['axis'];a=load_file(str(ASSET/manifest['layers'][str(l)]['file']));C=a['reading_matrix'].numpy();M=a['writing_matrix'].numpy();cos=lambda x,y:float(x@y/(np.linalg.norm(x)*np.linalg.norm(y)))
  ids=[s['id'] for s in samples if s['wrapper']=='W2_native' and s['target']=='奴才' and s['group'] in ['A1','A2','B','C']];rho=float(np.corrcoef(z[l,ids,c1],z[l,ids,c2])[0,1]);geometry.append(dict(layer=l,court_axis=c1,insult_axis=c2,same_axis=c1==c2,reading_cosine=cos(C[c1],C[c2]),writing_cosine=cos(M[:,c1],M[:,c2]),observed_score_correlation=rho));del a,C,M;gc.collect()
 save('axis_geometry.json',geometry);save('representative_readouts.json',rd)
 raw=[dict(id=p['id'],text=p['text'],target=p['target'],readings=[dict(name=x['name'],layer=x['layer'],axis=x['axis'],z_last=float(z[x['layer'],p['id'],x['axis']]),z_mean=float(zm[x['layer'],p['id'],x['axis']])) for x in reps]) for p in probes];save('representative_raw_scores.json',raw)
 save('validation.json',dict(all_scores_finite=bool(np.isfinite(z).all() and np.isfinite(zm).all()),projection_checks=checks,probe_count=n,probe_sha256=hashlib.sha256((R/'probes.json').read_bytes()).hexdigest(),causal_target_last=all(p['text'].endswith(p['target']) for p in probes),analysis_seconds=time.time()-start,full_data=fullpath,summary=compactpath))
 spec=__import__('importlib.util',fromlist=['spec_from_file_location']);s=spec.spec_from_file_location('exp1b_report',R/'report_exp1b.py');m=spec.module_from_spec(s);s.loader.exec_module(m);m.build(results,rd,reps,geometry,probes,pairs,samples);save('progress.json',dict(stage='complete',report=str(R/'report_exp1b.md')))
