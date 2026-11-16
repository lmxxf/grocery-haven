from common_exp2 import *
import sys,gc,math,gzip,re
import numpy as np,torch
import torch.nn.functional as F
from safetensors import safe_open
from scipy.stats import spearmanr
sys.path.insert(0,'/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-363')
from run_manifold_exp import compute_temporal_metrics_batched_layers as geometry,entropy_bits
LAYERS=[0,10,16,20,24,28,32,36,40,44,48,56,63]
PRIMARY=['s_geo','theta_surf','kappa_geo','erank_dir','pr_dir','top1_dir']
POEM_END={'rail_01':'低头思故乡。','rail_02':'粒粒皆辛苦。','rail_03':'花落知多少。','rail_04':'更上一层楼。','rail_09':'疑是银河落九天。','rail_10':'独钓寒江雪。','rail_11':'春风吹又生。','rail_12':'红掌拨清波。'}

def plan_extra(records):
 extra=[]
 for i,p in enumerate(['望庐山瀑布\n日照香炉生紫烟，','江雪\n千山鸟飞绝，','赋得古原草送别\n离离原上草，','咏鹅\n鹅，鹅，鹅，']):extra.append(dict(id=f'rail_{i+9:02d}',group='rail_clean_extra',prompt=p,max_new_tokens=48))
 extra.append(dict(id='cycle_positive_control',group='cycle_positive_control',prompt='校验记录，只按相同模式继续，不作解释：42，42，42，42，42，42，',max_new_tokens=120,expected='42'))
 extra.append(dict(id='arithmetic_direct_control',group='matched_direct',prompt='题目：计算(37×24−156)÷12。只写最后的数值，不写过程。\n答案：',max_new_tokens=48,expected='61'))
 append('Step 2 修正｜第一份解答与裸续写尾巴分开统计','首批rail_05~08不是干净直达续写：出现填空、模型自问下一题及生成<think>。前四条熟诗在首诗结束后也可能继续注释或复读。reason_01先真正算出61，再续写新题。原始序列全部保留；主对照限定首首完整诗与第一份解答，四条跑偏rail另作失败记录。\n\n补4条熟诗，凑满8条干净直达样本；加一条42固定模式正对照检查rank/周期检出，再加同算术题只答数值的对照。仍用驻留模型，不重载。裸续写未提出EOS时，屏蔽EOS不能被当作有效干预；后续要逐步比对自然/强制是否真的分叉。')
 return extra

def span_end(record):
 text=record['generated_text'];P=record['prompt_length'];ids=record['generated_ids'];cut=len(text);kind='budget_tail'
 if record['id'] in POEM_END:
  phrase=POEM_END[record['id']];pos=text.find(phrase)
  if pos>=0:cut=pos+len(phrase);kind='first_poem'
 elif record['group'] in ['reason','trap_pair','correction_seeded','port','matched_direct']:
  matches=list(re.finditer(r'\n\s*(?:题目|问题|解答|Question)[:：]',text))
  if matches:cut=matches[0].start();kind='before_next_item'
  if record['group'] in ['reason','port','matched_direct']:
   meta=text.find('<think>')
   if meta>=0 and meta<cut:cut=meta;kind='before_generated_meta_think'
  # Keep the first final answer line, not later documents/questions.
 count_tokens=sum(len(record['_tok'].decode(ids[:i+1]))<=cut for i in range(len(ids))) if '_tok'in record else len(ids)
 return P+max(1,count_tokens),kind

def scopes(record,tok):
 tmp=dict(record,_tok=tok);end,kind=span_end(tmp);P=record['prompt_length'];text=record['generated_text'];prefix_lengths=np.array([len(tok.decode(record['generated_ids'][:i+1])) for i in range(len(record['generated_ids']))])
 depth=1;close=None
 for j,ch in enumerate(text):
  if ch=='（':depth+=1
  elif ch=='）':
   depth-=1
   if depth==0:close=j;break
 closepos=next((P+i for i in range(len(record['generated_ids'])) if len(tok.decode(record['generated_ids'][:i+1]))>close and tok.decode(record['generated_ids'][:i+1])[close]=='）'),None) if close is not None else None
 markers=[]
 for match in re.finditer(r'等等|不对|算错|重新计算|重新算|纠正|更严谨|Wait|wait',text):
  at=next((P+i for i in range(len(record['generated_ids'])) if tok.decode(record['generated_ids'][:i+1])[match.start():match.end()]==match.group()),record['total_tokens']-1);markers.append(dict(text=match.group(),token_position=min(at,record['total_tokens']-1),character_position=match.start(),within_first_item=at<end))
 return dict(start=P,end=min(end,record['total_tokens']),kind=kind,closing_parenthesis_position=closepos,markers=markers,clean_rail=record['id']in POEM_END)

@torch.inference_mode()
def dynamics(model,record):
 path=H/record['id']/'kinematics.npz'
 if path.exists():return dict(np.load(path))
 source=np.load(record['raw_path'],mmap_mode='r');T=record['total_tokens'];metrics={k:np.empty((64,T),dtype='float32')for k in PRIMARY}
 for begin in range(0,64,8):
  h=torch.from_numpy(np.array(source[begin:begin+8,:T])).view(torch.bfloat16).to('cuda').float();m=geometry(h[:,None],torch.zeros((len(h),5120),device='cuda'))
  for k in PRIMARY:metrics[k][begin:begin+8]=m[k][:,0].cpu().numpy()
  del h,m
 h=torch.from_numpy(np.array(source[63,:T])).view(torch.bfloat16).to('cuda');Hs=[]
 for start in range(0,T,16):Hs.extend(entropy_bits(model.lm_head(model.model.norm(h[start:start+16]))).cpu().tolist())
 metrics['H_bits']=np.array(Hs,dtype='float32');errors=[abs(Hs[e['state_position']]-e['H_bits'])for e in record['decode_events']];metrics['entropy_cached_check_max']=np.array(max(errors,default=0.))
 np.savez_compressed(path,**metrics);del h;return metrics

@torch.inference_mode()
def project_all(records,features):
 manifest=read(V3/'hf_clean_upload/icalens.json');assetroot=V3/'hf_clean_upload'
 zfiles={r['id']:np.lib.format.open_memmap(H/r['id']/'ica_z.npy',mode='w+',dtype='float32',shape=(64,r['total_tokens'],5120))for r in records}
 for r in records:
  T=r['total_tokens'];f=features[r['id']]
  for name in ['zmax_positive','zmax_absolute','top5_energy','top20_energy','top5_positive_energy','kurt_d','positive_energy_fraction']+[f'deltaC_{t}'for t in [10,30,50]]+[f'deltaCpos_{t}'for t in [10,30,50]]+[f'deltaCposfull_{t}'for t in [10,30,50]]:f[name]=np.empty((64,T),dtype='float32')
  for name in ['top5_axis','top5_z','top5_kurtosis','bottom3_axis','bottom3_z']:f[name]=np.empty((64,T,5 if name.startswith('top5') else 3),dtype='int32'if name.endswith('axis')else'float32')
 for l in range(64):
  stats=read(V3/f'L{l:02d}/statistics.json')['test'];kurt=np.array(stats['excess_kurtosis']);masks={t:torch.tensor(kurt>t,device='cuda')for t in [10,30,50]}
  with safe_open(str(assetroot/manifest['layers'][str(l)]['file']),framework='pt',device='cuda')as st:C=st.get_tensor('reading_matrix');center=st.get_tensor('center')
  for r in records:
   source=np.load(r['raw_path'],mmap_mode='r');T=r['total_tokens'];h=torch.from_numpy(np.array(source[l,:T])).view(torch.bfloat16).to('cuda').float();z=(h/h.norm(dim=-1,keepdim=True).clamp_min(1e-12)-center)@C.T;zfiles[r['id']][l]=z.cpu().numpy();f=features[r['id']];sq=z.square();psq=z.clamp_min(0).square();energy=sq.sum(-1).clamp_min(1e-12);penergy=psq.sum(-1).clamp_min(1e-12)
   top=z.topk(5,dim=-1);bottom=z.topk(3,dim=-1,largest=False);topenergy=sq.topk(20,dim=-1).values;pe=psq.topk(5,dim=-1).values
   vals=dict(zmax_positive=z.clamp_min(0).amax(-1),zmax_absolute=z.abs().amax(-1),top5_energy=topenergy[:,:5].sum(-1)/energy,top20_energy=topenergy.sum(-1)/energy,top5_positive_energy=pe.sum(-1)/penergy,kurt_d=z.pow(4).mean(-1)/sq.mean(-1).square().clamp_min(1e-20)-3,positive_energy_fraction=penergy/energy)
   for t,mask in masks.items():
    fraction=float(mask.float().mean());vals[f'deltaC_{t}']=sq[:,mask].sum(-1)/energy-fraction;vals[f'deltaCpos_{t}']=psq[:,mask].sum(-1)/penergy-fraction;vals[f'deltaCposfull_{t}']=psq[:,mask].sum(-1)/energy-.5*fraction
   for name,value in vals.items():f[name][l]=value.cpu().numpy()
   f['top5_axis'][l]=top.indices.cpu().numpy();f['top5_z'][l]=top.values.cpu().numpy();f['top5_kurtosis'][l]=kurt[f['top5_axis'][l]];f['bottom3_axis'][l]=bottom.indices.cpu().numpy();f['bottom3_z'][l]=bottom.values.cpu().numpy();del h,z,sq,psq,energy,penergy,top,bottom
  for zfile in zfiles.values():zfile.flush()
  save('progress.json',dict(stage='ICA_projection',layer=l,total=64));print('PROJECTED',l,flush=True);del C,center;gc.collect()
 for r in records:np.savez_compressed(H/r['id']/'metrics.npz',**features[r['id']])
 del zfiles

def profile_labels(records,features):
 root=V3/'hf_clean_upload';manifest=read(root/'icalens.json');labels={}
 for l in range(64):
  file=R/'island_labels'/f'L{l:02d}.json'
  needed=set()
  for r in records:needed.update(int(x)for x in features[r['id']]['top5_axis'][l].ravel())
  if file.exists():
   saved=read(file)
   if needed<=set(map(int,saved)):labels[l]=saved;continue
  profile=json.loads(gzip.decompress((root/manifest['layers'][str(l)]['component_profile']).read_bytes()));out={}
  for c in needed:
   comp=profile['components'][c];j=comp['additional_readouts']['J Lens'];out[str(c)]=dict(axis=c,kurtosis=comp['score_statistics']['excess_kurtosis'],positive=j['positive']['top_tokens'][:5],negative=j['negative']['top_tokens'][:5])
  save(f'island_labels/L{l:02d}.json',out);labels[l]=out;del profile,out;gc.collect();print('LABELLED',l,len(needed),flush=True)
 return labels

def aggregate(records,features,scope,null):
 rows=[]
 for r in records:
  f=features[r['id']];s=scope[r['id']];ix=np.arange(max(s['start']+2,5),s['end']);group='rail_clean'if s['clean_rail']else r['group'];row=dict(id=r['id'],group=group,n_generated=len(r['generated_ids']),n_primary=len(ix),stop=r['stop_reason'],scope=s,layers={})
  for l in range(64):
   vals={k:float(np.mean(f[k][l,ix]))if len(ix)else None for k in ['s_geo','theta_surf','kappa_geo','erank_dir','zmax_positive','top5_energy','top20_energy','kurt_d','deltaC_10','deltaC_30','deltaC_50','deltaCpos_10','deltaCpos_30','deltaCpos_50']};gauss=(f['zmax_positive'][l,ix]<=null['zmax']['p95'])&(f['top20_energy'][l,ix]<=null['top20_energy']['p95'])&(f['kurt_d'][l,ix]<=null['coordinate_kurtosis']['p95']);vals['gaussian_like_fraction']=float(gauss.mean())if len(ix)else None;vals['H_bits']=float(f['H_bits'][ix].mean())if len(ix)else None
   vals['peak_kurt_gt10_fraction']=float((f['top5_kurtosis'][l,ix,0]>10).mean())if len(ix)else None
   h=f['H_bits'][ix];vals['spearman_H']={k:float(spearmanr(h,f[k][l,ix]).statistic)if len(ix)>5 and np.std(f[k][l,ix])>1e-8 and np.std(h)>1e-8 else None for k in ['s_geo','kappa_geo','erank_dir','zmax_positive','top20_energy','deltaC_10']};row['layers'][str(l)]=vals
  rows.append(row)
 groups={}
 for group in sorted({r['group']for r in rows}):
  rr=[r for r in rows if r['group']==group];groups[group]={str(l):{key:float(np.mean([r['layers'][str(l)][key]for r in rr if r['layers'][str(l)][key]is not None]))if any(r['layers'][str(l)][key]is not None for r in rr)else None for key in ['s_geo','kappa_geo','erank_dir','zmax_positive','top20_energy','kurt_d','deltaC_10','deltaC_30','deltaC_50','gaussian_like_fraction','H_bits']}for l in range(64)}
 return dict(cases=rows,groups=groups)

def landing_row(record,f,labels,l,t,k=3):
 islands=[]
 for c,z,ku in zip(f['top5_axis'][l,t,:k],f['top5_z'][l,t,:k],f['top5_kurtosis'][l,t,:k]):
  lab=labels[l][str(int(c))];islands.append(dict(axis=int(c),z=float(z),kurtosis=float(ku),words=[x['text']for x in lab['positive']],word_entries=lab['positive']))
 return dict(t=int(t),token_id=record['input_ids'][t],token=record['token_text'][t],raw_token=record['tokens'][t],layer=l,s=float(f['s_geo'][l,t]),theta=float(f['theta_surf'][l,t]),kappa_g=float(f['kappa_geo'][l,t]),rank5=float(f['erank_dir'][l,t]),H_next_bits=float(f['H_bits'][t]),deltaC10=float(f['deltaC_10'][l,t]),deltaC30=float(f['deltaC_30'][l,t]),deltaC50=float(f['deltaC_50'][l,t]),zmax=float(f['zmax_positive'][l,t]),top20=float(f['top20_energy'][l,t]),kurt_d=float(f['kurt_d'][l,t]),islands=islands)

def serial_clean(obj):
 if isinstance(obj,float):return obj if math.isfinite(obj)else None
 if isinstance(obj,dict):return{k:serial_clean(v)for k,v in obj.items()}
 if isinstance(obj,list):return[serial_clean(v)for v in obj]
 return obj

def run(model,tok,records,rounds):
 if rounds==0 and not any(r['id']=='rail_09'for r in records):return plan_extra(records)
 null=read(R/'calibration.json');features={};scope={r['id']:scopes(r,tok)for r in records}
 for r in records:
  file=H/r['id']/'metrics.npz';features[r['id']]=dict(np.load(file))if file.exists()else dynamics(model,r)
 if not all('zmax_positive'in f for f in features.values()):project_all(records,features)
 summary=aggregate(records,features,scope,null);save('summary.json',serial_clean(summary));save('scope.json',scope)
 # Reading labels follows the quantitative checkpoint, so failed hypotheses stay in the ledger.
 append('Step 2 首轮量化｜先记读数，再给岛挂名字','全64层ICA与原363运动学已联立。8条首诗与8条第一份推理的case均值已写summary.json；原始全序列指标metrics.npz留重数据目录。\n\nL32首诗/推理：`'+json.dumps({g:summary['groups'].get(g,{}).get('32')for g in ['rail_clean','reason']},ensure_ascii=False)+'`。\n\n这里先冻结数字，随后再读J-Lens词牌；不能看词牌后挑一条漂亮路线冒充整组。')
 labels=profile_labels(records,features)
 for r in records:
  s=scope[r['id']];f=features[r['id']];trace=dict(id=r['id'],scope=s,layers={str(l):[landing_row(r,f,labels,l,t)for t in range(max(s['start'],5),min(s['end'],r['total_tokens']))]for l in [16,32,40,63]});save(f'traces/{r["id"]}_navigation.json',serial_clean(trace))
 import importlib.util
 spec=importlib.util.spec_from_file_location('exp2_history',R/'write_history_exp2.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.run(model,tok,records,features,scope,labels,summary,null)
 return []
