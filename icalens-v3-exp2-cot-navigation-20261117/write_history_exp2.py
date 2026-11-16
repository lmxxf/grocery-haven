from common_exp2 import *
import json,re,math,gc
from collections import Counter
import numpy as np,torch
from analyze_exp2 import landing_row,serial_clean,dynamics,project_all,profile_labels,aggregate,scopes

def fmt(x):return 'NA'if x is None or not np.isfinite(x)else f'{x:.4g}'
def escape(s):return json.dumps(s,ensure_ascii=False).replace('|','\\|')
def plaque(row):return ' ; '.join(f"C{x['axis']} z={x['z']:.2f} κ={x['kurtosis']:.1f} [{', '.join(escape(w)for w in x['words'])}]"for x in row['islands'])
def token_index(r,tok,text):
 pos=r['generated_text'].find(text)
 if pos<0:return None
 for i in range(len(r['generated_ids'])):
  if tok.decode(r['generated_ids'][:i+1])[pos:pos+len(text)]==text:return r['prompt_length']+i
 return None

def window(r,f,scope,labels,pivot,title,k=5):
 lo=max(5,pivot-4);hi=min(r['total_tokens'],pivot+5);rows=[landing_row(r,f,labels,32,t,k=k)for t in range(lo,hi)];text=title+'\n\n|t|真实token|s|θ|κ_g|rank5|H_next|ΔC10|Top20|Top-'+str(k)+'正极岛与J-Lens原词牌|\n|---|---|---|---|---|---|---|---|---|---|\n'
 for x in rows:text+=f"|{x['t']}|{escape(x['token'])}|{fmt(x['s'])}|{fmt(x['theta'])}|{fmt(x['kappa_g'])}|{fmt(x['rank5'])}|{fmt(x['H_next_bits'])}|{fmt(x['deltaC10'])}|{fmt(x['top20'])}|{plaque(x)}|\n"
 if pivot>0:
  z=np.load(H/r['id']/'ica_z.npy',mmap_mode='r');old=int(f['top5_axis'][32,pivot-1,0]);new=int(f['top5_axis'][32,pivot,0]);cross=dict(old_axis=old,new_axis=new,old_before=float(z[32,pivot-1,old]),old_now=float(z[32,pivot,old]),new_before=float(z[32,pivot-1,new]),new_now=float(z[32,pivot,new]),top5_overlap=len(set(map(int,f['top5_axis'][32,pivot-1]))&set(map(int,f['top5_axis'][32,pivot]))))
  text+='\n前后主岛交叉读数：`'+json.dumps(cross,ensure_ascii=False)+'`。κ_g=θ/平均步长，表里同时保留θ和s，避免把速度变小导致的比值变大全说成方向盘突然更猛。\n'
 return text,rows

@torch.inference_mode()
def permutation_ablation(records,features,scope,null):
 candidates=[]
 for r in records:
  if r['group']!='reason':continue
  f=features[r['id']];s=scope[r['id']]
  for t in range(max(5,s['start']+2),s['end']):
   if f['zmax_positive'][32,t]>null['zmax']['p99']:candidates.append((float(f['deltaC_10'][32,t]),r,t))
 if not candidates:return None
 _,r,t=min(candidates,key=lambda x:x[0]);z=np.load(H/r['id']/'ica_z.npy',mmap_mode='r');vector=torch.tensor(np.array(z[32,t]),device='cuda');squared=vector.square();kurt=np.array(read(V3/'L32/statistics.json')['test']['excess_kurtosis']);mask=torch.tensor(kurt>10,device='cuda');count=int(mask.sum());torch.manual_seed(36317);vals=[]
 for j in range(256):vals.append(float(squared[torch.randperm(5120,device='cuda')[:count]].sum()/squared.sum())-count/5120)
 out=dict(case=r['id'],t=t,token=r['token_text'][t],real_deltaC10=float(features[r['id']]['deltaC_10'][32,t]),zmax=float(features[r['id']]['zmax_positive'][32,t]),top20=float(features[r['id']]['top20_energy'][32,t]),kurt_d=float(features[r['id']]['kurt_d'][32,t]),peak_axis=int(features[r['id']]['top5_axis'][32,t,0]),peak_axis_kurtosis=float(features[r['id']]['top5_kurtosis'][32,t,0]),permutations=256,permuted_delta_mean=float(np.mean(vals)),permuted_p05=float(np.quantile(vals,.05)),permuted_p95=float(np.quantile(vals,.95)))
 save('mask_permutation_ablation.json',out);return out

def port_stats(r,f,labels,aligned_arm=None):
 P=r['prompt_length'];arm=aligned_arm if aligned_arm is not None else r.get('forced_at_generated_index');arm=P+arm if arm is not None else P+max(8,len(r['generated_ids'])//3);end=r['total_tokens'];before=np.arange(max(5,P),max(max(5,P)+1,arm));after=np.arange(min(end,arm+5),end);l=32
 def summarize(ix):
  if not len(ix):return None
  counts=Counter(map(int,f['top5_axis'][l,ix,0]));top=counts.most_common(6)
  return dict(n=len(ix),rank5=float(f['erank_dir'][l,ix].mean()),s=float(f['s_geo'][l,ix].mean()),kappa=float(f['kappa_geo'][l,ix].mean()),H=float(f['H_bits'][ix].mean()),zmax=float(f['zmax_positive'][l,ix].mean()),top20=float(f['top20_energy'][l,ix].mean()),unique_main_islands=len(counts),top3_main_coverage=sum(v for _,v in top[:3])/len(ix),top4_main_coverage=sum(v for _,v in top[:4])/len(ix),islands=[dict(axis=c,count=n,words=[x['text']for x in labels[l][str(c)]['positive']])for c,n in top])
 result=dict(id=r['id'],arm=arm,arm_reason=r.get('forced_reason'),first_eos=r.get('first_eos_proposal'),extra=r.get('actual_extra_after_arm'),before=summarize(before),after=summarize(after),eos_mass_max=max((e['eos_raw_probability']for e in r['decode_events']),default=0.))
 # Independent recurrence check on actual unit residuals; rank5 alone does not prove a loop.
 if len(after)>32:
  src=np.load(r['raw_path'],mmap_mode='r');x=torch.from_numpy(np.array(src[32,:end])).view(torch.bfloat16).float();u=x/x.norm(dim=1,keepdim=True).clamp_min(1e-12);scores=[]
  for lag in range(2,33):
   ix=after[after>=lag];scores.append((float((u[ix]*u[ix-lag]).sum(-1).mean()),lag))
  best=max(scores);result['recurrence_best_lag']=best[1];result['recurrence_mean_cosine']=best[0]
 return result


def supplement_real_eos(model,tok,records,features,scope,labels,summary,null):
 if any(r['id']=='port_eos_direct_forced'for r in records):return labels,summary
 from generate_exp2 import generate
 append('Step 4 补跑决定｜先找真正提出EOS的正确短答', '初始sum/mul强制臂在答案后96步已结束，而自然臂相同前缀没有EOS，不能验证屏蔽EOS因果。另一个同算术只答数值对照虽然3步就提出EOS，却答成55（正确61），原样保留。现在用驻留模型补一个简单算式短答，只有答对且确实提出EOS才配对强制96步。')
 new=[];natural=None
 for attempt,(problem,answer) in enumerate([('23+19','42'),('7×8','56'),('1+1','2')]):
  case=dict(id='port_eos_probe_'+str(attempt),group='eos_probe',prompt='题目：计算'+problem+'。只写最后的数值，不写过程。\n答案：',max_new_tokens=24,expected=answer)
  r=generate(model,tok,case);records.append(r);new.append(r)
  if r['first_eos_proposal'] is not None and re.fullmatch(r'\s*'+re.escape(answer)+r'[。.\s]*',r['generated_text']):natural=r;break
 if natural is not None:
  natural['port_pair']='eos_direct';natural['eos_control_eligible']=True
  forced_case=dict(id='port_eos_direct_forced',group='port_eos_actual',prompt=natural['prompt'],max_new_tokens=len(natural['generated_ids'])+104,expected=natural['expected'],force_eos=True,extra_after_stop=96,port_pair='eos_direct')
  forced=generate(model,tok,forced_case);records.append(forced);new.append(forced)
  save('real_eos_pair.json',dict(natural_id=natural['id'],forced_id=forced['id'],expected=natural['expected']))
 else:append('Step 4 补跑负结果｜没凑造EOS因果对照','三个短答尝试中没有同时满足“正确答案+真实EOS提议”的样本，保留失败，不把budget停止说成EOS停止。')
 save('completed_cases.json',[r['id']for r in records])
 new_features={}
 for r in new:new_features[r['id']]=dynamics(model,r);scope[r['id']]=scopes(r,tok)
 project_all(new,new_features);features.update(new_features);labels=profile_labels(records,features);summary=aggregate(records,features,scope,null);save('summary.json',serial_clean(summary));save('scope.json',scope)
 return labels,summary

def run(model,tok,records,features,scope,labels,summary,null):
 labels,summary=supplement_real_eos(model,tok,records,features,scope,labels,summary,null)
 lookup={r['id']:r for r in records};rows=['8条干净首诗与8条第一份推理按case等权平均；rail_05~08原失败样本另留，不混进干净对照。坐标κ阈值只是轴在大样本中的重尾属性；当前token是否尖峰另看z_max、Top20与Kurt_d。','', '|层|组|H bits|s|κ_g|rank5|z_max+|Top20能量|跨维Kurt_d|ΔC10|ΔC30|ΔC50|高斯样比例|','|---|---|---|---|---|---|---|---|---|---|---|---|']
 for l in [0,10,16,20,24,32,40,48,63]:
  for group in ['rail_clean','reason']:
   g=summary['groups'][group][str(l)];rows.append('|'+str(l)+'|'+group+'|'+'|'.join(fmt(g[k])for k in ['H_bits','s_geo','kappa_geo','erank_dir','zmax_positive','top20_energy','kurt_d','deltaC_10','deltaC_30','deltaC_50','gaussian_like_fraction'])+'|')
 rows+=['','高斯样的操作判据：z_max≤高斯95分位且Top20≤高斯95分位且Kurt_d≤高斯95分位，三者同时满足。L00 κ>10比例为1，ΔC10恒约0，不能据此把L00全判成海或陆。','', '### 括号内是否已提前到站：逐case对账','', '|case|首个全角闭括号t|草稿s / 答案s|草稿zmax / 答案zmax|草稿Top20 / 答案Top20|草稿rank / 答案rank|','|---|---|---|---|---|---|']
 phase=[]
 for r in records:
  if r['group']!='reason':continue
  s=scope[r['id']];f=features[r['id']];c=s['closing_parenthesis_position'];before=np.arange(max(5,s['start']+2),c)if c is not None else np.array([],int);after=np.arange(c+1,s['end'])if c is not None else np.array([],int)
  if not len(before)or not len(after):rows.append(f"|{r['id']}|{c}|无足够括号内/外样本|—|—|—|");continue
  v={name:[float(f[name][32,ix].mean())for ix in [before,after]]for name in ['s_geo','zmax_positive','top20_energy','erank_dir']};phase.append(dict(id=r['id'],closing=c,before=len(before),after=len(after),metrics=v));rows.append(f"|{r['id']}|{c}|"+'|'.join(' / '.join(fmt(x)for x in v[k])for k in ['s_geo','zmax_positive','top20_energy','erank_dir'])+'|')
 save('phase_comparison.json',phase);append('Step 2 实测｜海陆×运动学首轮对账','\n'.join(rows))
 ablation=permutation_ablation(records,features,scope,null)
 if ablation:append('Step 2 补刀｜负ΔC不等于真的潜入高斯海','在已存在尖峰的推理token中，挑L32 ΔC10最低的一步，只打乱“哪些轴算κ>10”的标签，不改z本身。256次轴标签置换：\n\n```json\n'+json.dumps(ablation,ensure_ascii=False,indent=2)+'\n```\n\nz_max、Top20、Kurt_d保持完全不变。若真实ΔC偏低却仍尖峰很高，应区分“能量落在低κ通道”与“向量各维高斯平摊”，不能把它们叫成同一种深海。')
 # One entire first solution/poem trace, token by token, with genuine Top3 plaques.
 for ident,title in [('rail_01','熟句首诗'),('reason_01','多步算术第一份解答')]:
  r=lookup[ident];s=scope[ident];f=features[ident];text=title+'，L32逐token原始登岛，不给轴重新编故事名。\n\n|t|真实token|H_next|s|κ_g|ΔC10|z_max|Top20|Top3正极岛 / J-Lens Top5原词|\n|---|---|---|---|---|---|---|---|---|\n';trace=[]
  for t in range(max(5,s['start']),min(s['end'],s['start']+48)):
   x=landing_row(r,f,labels,32,t);trace.append(x);text+=f"|{t}|{escape(x['token'])}|{fmt(x['H_next_bits'])}|{fmt(x['s'])}|{fmt(x['kappa_g'])}|{fmt(x['deltaC10'])}|{fmt(x['zmax'])}|{fmt(x['top20'])}|{plaque(x)}|\n"
  append('Step 2 显微航线｜'+ident,text)
 # Six paired traps, then two strongest correction/turning windows.
 paired=['正常/陷阱只比较同一pair，所有真实输出留在前面的生成条目。数字为第一份生成解答L32的均值，不把题干的换字冲击偷算成已经生成的顿悟。','', '|pair|variant|H|s|κ_g|rank5|ΔC10|z_max|Top20|','|---|---|---|---|---|---|---|---|---|']
 for row in summary['cases']:
  r=lookup[row['id']]
  if r['group']!='trap_pair':continue
  g=row['layers']['32'];paired.append('|'+r['pair']+'|'+r['variant']+'|'+'|'.join(fmt(g[k])for k in ['H_bits','s_geo','kappa_geo','erank_dir','deltaC_10','zmax_positive','top20_energy'])+'|')
 append('Step 3 实测｜六组孪生陷阱', '\n'.join(paired))
 index=['每条孪生轨迹在首份输出内取自身L32最大κ_g位置，完整前后各4 token与Top5原词牌另存JSON；不预先认定此峰就是顿悟。','']
 for r in records:
  if r['group']!='trap_pair':continue
  f=features[r['id']];ss=scope[r['id']];ix=np.arange(max(5,ss['start']+2),ss['end'])
  if not len(ix):continue
  t=int(ix[np.nanargmax(f['kappa_geo'][32,ix])]);_,win=window(r,f,ss,labels,t,'自动κ峰',k=5);path='events/'+r['id']+'_peak.json';save(path,serial_clean(win));x=landing_row(r,f,labels,32,t,k=1);index.append(f"- {r['id']} t={t} token={escape(x['token'])}，κ_g={fmt(x['kappa_g'])}，θ={fmt(x['theta'])}，s={fmt(x['s'])}，ΔC10={fmt(x['deltaC10'])}，主岛{plaque(x)}：[8步完整窗口]({path})")
 append('Step 3 全样本索引｜12条轨迹的真实κ峰与前后8步', '\n'.join(index))
 candidates=[]
 for r in records:
  for mark in scope[r['id']]['markers']:
   if mark['within_first_item']:candidates.append((r,mark))
 unseeded=[p for p in candidates if not p[0].get('seeded_error')];seeded=[p for p in candidates if p[0].get('seeded_error')];events=[]
 for bucket in [unseeded,seeded]:
  if bucket:
   r,m=max(bucket,key=lambda p:float(features[p[0]['id']]['kappa_geo'][32,p[1]['token_position']]));events.append((r,m['token_position'],'模型生成标记'+m['text']+'；'+('错误初稿由外部注入'if r.get('seeded_error')else'未注入错误初稿')))
 if not events:
  candidates2=[]
  for r in records:
   if r['group']!='trap_pair':continue
   f=features[r['id']];s=scope[r['id']];ix=np.arange(max(5,s['start']+2),s['end'])
   if len(ix):t=int(ix[np.nanargmax(f['kappa_geo'][32,ix])]);candidates2.append((float(f['kappa_geo'][32,t]),r,t))
  if candidates2:
   _,r,t=max(candidates2,key=lambda x:x[0]);events.append((r,t,'未采到第一份解答内的纠错词；只展示陷阱轨迹最高κ_g，不冒充顿悟'))
 for r,t,title in events:
  text,win=window(r,features[r['id']],scope[r['id']],labels,t,title);save('events/'+r['id']+f'_{t}.json',serial_clean(win));append('Step 3 显微急转弯｜'+r['id'],text)
 # A genuine same-token, all-layer section for poem, arithmetic answer and turn marker.
 selections=[]
 p=lookup['rail_01'];t=token_index(p,tok,'明月');t=t if t is not None else p['prompt_length']+2;selections.append((p,t,'首诗中生成的明月词元'))
 p=lookup['reason_01'];t=token_index(p,tok,'61');t=t if t is not None else scope[p['id']]['end']-1;selections.append((p,t,'算术第一份解答中的61'))
 if events:selections.append((events[0][0],events[0][1],'急转弯或纠错标记词元'))
 vertical=[]
 for r,t,title in selections:
  f=features[r['id']];text=f"{title}：{r['id']} t={t}，真实token={escape(r['token_text'][t])}。每层C编号是该层自己的轴，不把同一个编号跨层当成同一座岛。\n\n|L|ΔC10|ΔC30|ΔC50|z_max|Top20|Kurt_d|从上一层的球面步长|Top3正极轴 / J-Lens Top5原词|\n|---|---|---|---|---|---|---|---|---|\n";src=np.load(r['raw_path'],mmap_mode='r');h=torch.from_numpy(np.array(src[:,t])).view(torch.bfloat16).float();u=h/h.norm(dim=1,keepdim=True).clamp_min(1e-12);v=torch.acos((u[1:]*u[:-1]).sum(-1).clamp(-1,1)).numpy();section=[]
  for l in range(64):
   x=landing_row(r,f,labels,l,t);x['vertical_step']=None if l==0 else float(v[l-1]);section.append(x);text+=f"|{l:02d}|{fmt(x['deltaC10'])}|{fmt(x['deltaC30'])}|{fmt(x['deltaC50'])}|{fmt(x['zmax'])}|{fmt(x['top20'])}|{fmt(x['kurt_d'])}|{fmt(x['vertical_step'])}|{plaque(x)}|\n"
  vertical.append(dict(case=r['id'],token=t,title=title,layers=section));append('Step 4 纵向穿海剖面｜'+r['id']+f' t={t}',text)
 save('vertical_sections.json',serial_clean(vertical))
 ports=[];comparisons=[]
 for name in ['sum','mul']:
  natural=lookup['port_'+name+'_natural'];forced=lookup['port_'+name+'_forced'];a=natural['generated_ids'];b=forced['generated_ids'];same=0
  for x,y in zip(a,b):
   if x!=y:break
   same+=1
  cmp=dict(pair=name,natural_generated=len(a),forced_generated=len(b),common_prefix=same,all_common_tokens_identical=same==min(len(a),len(b)),natural_first_eos=natural['first_eos_proposal'],forced_first_eos=forced['first_eos_proposal'],forced_arm=forced['forced_at_generated_index'],forced_reason=forced['forced_reason'],forced_extra=forced['actual_extra_after_arm']);comparisons.append(cmp)
  for r in [natural,forced]:ports.append(port_stats(r,features[r['id']],labels,aligned_arm=forced['forced_at_generated_index']))
 if (R/'real_eos_pair.json').exists():
  ep=read(R/'real_eos_pair.json');a=lookup[ep['natural_id']];b=lookup[ep['forced_id']];same=0
  for x,y in zip(a['generated_ids'],b['generated_ids']):
   if x!=y:break
   same+=1
  comparisons.append(dict(pair='eos_direct_actual',natural_id=a['id'],forced_id=b['id'],natural_generated=len(a['generated_ids']),forced_generated=len(b['generated_ids']),common_prefix=same,all_common_tokens_identical=same==len(a['generated_ids']),natural_first_eos=a['first_eos_proposal'],forced_first_eos=b['first_eos_proposal'],forced_arm=b['forced_at_generated_index'],forced_reason=b['forced_reason'],forced_extra=b['actual_extra_after_arm']))
  for r in [a,b]:ports.append(port_stats(r,features[r['id']],labels,aligned_arm=b['forced_at_generated_index']))
 if 'cycle_positive_control'in lookup:ports.append(port_stats(lookup['cycle_positive_control'],features['cycle_positive_control'],labels))
 save('port_comparisons.json',comparisons);save('port_metrics.json',serial_clean(ports));body='先核验干预是否真的改变了token序列，再看rank与停留岛。若自然续写本来就没有EOS候选，不能把两条相同轨迹的差异归因于屏蔽EOS。\n\n```json\n'+json.dumps(comparisons,ensure_ascii=False,indent=2)+'\n```\n\n|case|分段|n|rank5|s|H|z_max|Top20|主岛数|Top3主岛覆盖|Top4主岛覆盖|\n|---|---|---|---|---|---|---|---|---|---|---|\n'
 for port in ports:
  for phase in ['before','after']:
   q=port[phase]
   if q:body+=f"|{port['id']}|{phase}|{q['n']}|{fmt(q['rank5'])}|{fmt(q['s'])}|{fmt(q['H'])}|{fmt(q['zmax'])}|{fmt(q['top20'])}|{q['unique_main_islands']}|{fmt(q['top3_main_coverage'])}|{fmt(q['top4_main_coverage'])}|\n"
  if port['after']:body+='\n'+port['id']+'尾段主岛与原词牌：`'+json.dumps(port['after']['islands'],ensure_ascii=False)+'`；独立周期检验 lag='+str(port.get('recurrence_best_lag'))+'，平均cos='+fmt(port.get('recurrence_mean_cosine'))+'。\n\n'
 append('Step 4 实测｜EOS屏蔽是否有效、港口是否真的兜圈',body)
 # Compact actual phase plot, scientific static artifact (not an interactive mockup).
 try:
  import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
  fig,ax=plt.subplots(4,1,figsize=(11,9),sharex=True)
  for ident,color in [('reason_01','#d97706'),('port_sum_forced','#0284c7'),('cycle_positive_control','#8b5cf6')]:
   if ident not in lookup:continue
   r=lookup[ident];f=features[ident];ix=np.arange(r['prompt_length'],r['total_tokens']);x=ix-r['prompt_length']
   for a,key in zip(ax,['s_geo','kappa_geo','erank_dir','zmax_positive']):a.plot(x,f[key][32,ix],label=ident,color=color,lw=1)
  for a,label in zip(ax,['Geodesic step','Geodesic curvature','5-step tangent rank','Positive peak z']):a.set_ylabel(label);a.grid(alpha=.2)
  ax[0].legend(fontsize=8);ax[-1].set_xlabel('Generated token index (L32)');fig.tight_layout();fig.savefig(R/'navigation_L32.svg');plt.close(fig);append('Step 4 图像落盘','四指标同图：![L32真实轨迹](navigation_L32.svg)。橙色原算术、蓝色强制续写、紫色固定重复正对照。图展示实际数值，不把三条不同提示当成严格同题干预。')
 except Exception as e:append('绘图未完成',repr(e)+'；全部数值与词牌已经落盘，不影响数据读取。')
 # Save a short factual entry point, not a formal report.
 readme=['# ICA-Lens v3 思维链航海实验','', '从 [DevHistory.md](DevHistory.md) 按时间读。这里保留第一版样本跑偏、补跑、指标修正及逐token真实词牌，不另造论文式报告。','',f'共{len(records)}条真实生成轨迹；全64层；裸文本；一次完整27B驻留。','', '入口：cases.json（初批）、extra_cases.json（补跑）、summary.json（case等权全层摘要）、traces/（原始生成+逐token航线）、island_labels/（v3内置J-Lens原词牌）、port_comparisons.json（先看EOS干预是否有效）、phase_comparison.json、vertical_sections.json。',f'原始BF16残差、全轴ICA坐标与metrics.npz均只在 `{H}`。','', '高斯校准：calibration.json。z_max、Top20、跨维峰度与ΔC共同看；L00 ΔC10饱和不能判海陆。', '', '复现：bash run_all.sh；heavy目录中已有metrics时可只重建航线解析。生成脚本保留原始概率、特殊token过滤与EOS屏蔽记录。']
 (R/'README.md').write_text('\n'.join(readme)+'\n');save('validation.json',dict(cases=len(records),layers=64,all_have_raw=all(Path(r['raw_path']).exists()for r in records),all_have_metrics=all((H/r['id']/'metrics.npz').exists()for r in records),entropy_max_cached_vs_recomputed=max(float(features[r['id']]['entropy_cached_check_max'])for r in records),all_metrics_finite_after_valid_prefix=all(np.isfinite(features[r['id']]['erank_dir'][:,5:]).all()for r in records)))
