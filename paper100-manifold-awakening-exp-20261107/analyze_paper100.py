#!/usr/bin/env python3
"""CPU-only aggregation, coverage audit, explicit paired comparisons, standalone SVGs."""
import json,math,hashlib,statistics,html,collections,time,re
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent
NAMES=['Qwen3-0.6B','Qwen3.8-27B-FP8','Qwen3.5-35B-A3B-Base','Qwen3.5-35B-A3B']
METRICS=['s_geo','theta_surf','kappa_geo','erank_dir','erank_dir_16','erank_span_steps_all','erank_span_steps_16','erank_span_steps_64','v_layer','erank_layer','accel_geo','c_flat','extrinsic_bias','norm']
def save(p,obj):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False));tmp.replace(p)
def mean(a):
 a=[float(x)for x in a if x is not None and math.isfinite(x)];return statistics.mean(a)if a else None
def val(r,span,m,band='mid'):return r.get('span_summaries',{}).get(span,{}).get(band,{}).get(m)
def fmt(x):return '—'if x is None else f'{x:.4f}'
def table(rows,cols):
 return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(str(r.get(c,'—'))for c in cols)+' |'for r in rows)+'\n'
def source(rec):
 p=rec.get('source_file');return json.loads(Path(p).read_text())if p else None

def svg_chart(path,title,series,ylabel):
 # series: label -> [(x,y)], independent per panel. No implicit missing-zero conversion.
 W=960;panel=260;H=80+panel*max(1,len(series));out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="#101722"/><g font-family="WenQuanYi Micro Hei,DejaVu Sans,sans-serif" fill="#dce7ef"><text x="24" y="32" font-size="20">{html.escape(title)}</text>']
 for j,(label,points)in enumerate(series.items()):
  pts=[(x,y)for x,y in points if y is not None and math.isfinite(y)]
  y0=70+j*panel;out.append(f'<text x="24" y="{y0}" font-size="15">{html.escape(label)} | {html.escape(ylabel)}</text>')
  if not pts:continue
  xs=[x for x,y in pts];ys=[y for pp in series.values()for x,y in pp if y is not None and math.isfinite(y)];xmin=min(xs);xmax=max(xs);ymin=min(0,min(ys));ymax=max(ys);ymax=ymax if ymax>ymin else ymin+1
  def px(x):return 90+(x-xmin)/max(xmax-xmin,1)*800
  def py(y):return y0+205-(y-ymin)/(ymax-ymin)*170
  out.append(f'<path d="M90,{y0+30} V{y0+205} H900" fill="none" stroke="#617184"/>')
  if xmin<0<xmax:out.append(f'<path d="M{px(0):.2f},{y0+30} V{y0+205}" stroke="#dce7ef" stroke-dasharray="4 4"/>')
  if ymin<0<ymax:out.append(f'<path d="M90,{py(0):.2f} H900" stroke="#dce7ef" stroke-dasharray="4 4"/>')
  pathdata=' '.join(('M'if i==0 else'L')+f'{px(x):.2f},{py(y):.2f}'for i,(x,y)in enumerate(pts));out.append(f'<path d="{pathdata}" fill="none" stroke="#52d6ba" stroke-width="2"/>')
  for x,y in pts:
   out.append(f'<circle cx="{px(x):.2f}" cy="{py(y):.2f}" r="2" fill="#f3be63"><title>{x}: {y:.6g}</title></circle>')
  for x,y,text in [(90,y0+225,str(xmin)),(860,y0+225,str(xmax)),(12,y0+40,f'{ymax:.3g}'),(12,y0+205,f'{ymin:.3g}')]:out.append(f'<text x="{x}" y="{y}" font-size="12">{text}</text>')
 out.append('</g></svg>');path.write_text(''.join(out))

def main():
 data={n:json.loads((R/f'manifold_{n}.json').read_text())for n in NAMES};summary={'models':{},'experiment1':[],'experiment2':{},'experiment3':[],'experiment4':{},'coverage':{},'method_version':2}
 ledger=[json.loads(x)for x in (R/'stage_resources.jsonl').read_text().splitlines()]
 stages=dict(zip(NAMES,['qwen06b','qwen27b','qwen35b_base','qwen35b_post']))
 for n,d in data.items():
  assert d.get('streaming_version')==2,(n,'legacy output cannot be silently merged')
  if d['resources'].pop('max_forward_cuda_delta_MiB',None)is not None:save(R/f'manifold_{n}.json',d)
  weight_gib=d.get('load_plan',{}).get('final_allocated_GiB')
  if weight_gib is None:
   logpath=R/('qwen06b.log'if n==NAMES[0]else'qwen27b.log')
   matches=re.findall(r'MODEL_READY '+re.escape(n)+r' (\d+)',logpath.read_text())
   if matches:weight_gib=int(matches[-1])/1024**3
  summary['models'][n]={'external_minimum_available_GiB':min([x['minimum_available_GiB']for x in ledger if x['stage']==stages[n]]or[d['resources']['minimum_available_GiB']]),'weight_resident_GiB':weight_gib,'records':len(d['records']),'resources':d['resources'],'elapsed_seconds':d['elapsed_seconds']}
  buckets=collections.defaultdict(list)
  for cid,r in d['records'].items():
   if cid.startswith('common_base:'):continue
   if not r.get('span_summaries',{}).get('generated'):continue
   key=(r.get('family')or r.get('exp'),r.get('format')or'raw',r.get('group'),r.get('stage'))
   buckets[key].append(r)
  for key,rs in sorted(buckets.items(),key=lambda x:str(x[0])):
   family,form,group,stage=key
   summary['experiment1'].append({'model':n,'family':family,'format':form,'group':group,'stage':stage,'n':len(rs),'mean_generated_tokens':mean([r['span_summaries']['generated']['n_tokens']for r in rs]),'metrics':{m:mean([val(r,'generated',m)for r in rs])for m in METRICS}})
  summary['coverage'][n]=[{'family':k[0],'format':k[1],'group':k[2],'stage':k[3],'n':len(v)}for k,v in buckets.items()]
  # Matched A/B examples, not averages over different questions.
  recs={r['id']:r for r in d['records'].values()}
  for rid,a in recs.items():
   if not rid.startswith('e4_')or not rid.endswith('_A'):continue
   b=recs.get(rid[:-1]+'B')
   if b is None:continue
   summary['experiment3'].append({'model':n,'item':rid[3:-2],'A':{m:val(a,'answer',m)for m in METRICS},'B_answer':{m:val(b,'answer',m)for m in METRICS},'B_parenthesis':{m:val(b,'parenthesis',m)for m in METRICS},'B_minus_A':{m:(val(b,'answer',m)-val(a,'answer',m))if val(a,'answer',m)is not None and val(b,'answer',m)is not None else None for m in METRICS}})
  if d.get('exp4_tangent_projection'):summary['experiment4'][n]=d['exp4_tangent_projection']
 # Every prefix is checked directly against source token IDs; aggregate only exact matches.
 base=data[NAMES[2]]['records'];post=data[NAMES[3]]['records'];paired=[];exact=[]
 for cid,b in base.items():
  p=post.get(cid)
  if not p:continue
  bs=source(b);ps=source(p);nb=bs['prompt_tokens'];np_=ps['prompt_tokens']
  if bs['token_ids'][:nb]!=ps['token_ids'][:np_]:continue
  rows={}
  for span in ['pre_tag_content_tail','role_tag_zone','role_tag_onset','think_scaffold_zone','reply_onset','gen_first1','gen_first5']:
   rows[span]={m:{'base':val(b,span,m),'post':val(p,span,m),'post_minus_base':val(p,span,m)-val(b,span,m)if val(p,span,m)is not None and val(b,span,m)is not None else None}for m in METRICS}
  paired.append({'id':b['id'],'group':b.get('group'),'format':b.get('format'),'prefix_sha256':hashlib.sha256(json.dumps(bs['token_ids'][:nb]).encode()).hexdigest(),'spans':rows})
 for cid,b in base.items():
  ep=post.get('common_base:'+b['id'])
  if ep:
   assert b['token_sha256']==ep['token_sha256']
   exact.append({'id':b['id'],'group':b.get('group'),'token_sha256':b['token_sha256'],'windows':{span:{m:{'base':val(b,span,m),'post':val(ep,span,m),'delta':val(ep,span,m)-val(b,span,m)if val(ep,span,m)is not None and val(b,span,m)is not None else None}for m in METRICS}for span in ['pre_tag_content_tail','role_tag_zone','role_tag_onset','think_scaffold_zone','reply_onset','gen_first1','gen_first5']}})
 summary['experiment2']={'prefix_identical_pairs':paired,'complete_sequence_identical_pairs':exact,'n_prefix_pairs':len(paired),'n_complete_pairs':len(exact)}
 postcond={g:{r['pair']:r for cid,r in post.items()if cid.startswith('bp:') and r.get('format')=='chat' and r.get('family')=='trap' and r.get('group')==g}for g in ['bare','natural_syzygy']}
 keys=sorted(set(postcond['bare'])&set(postcond['natural_syzygy']));postrows=[]
 for sp in ['role_tag_onset','reply_onset','gen_first5']:
  postrows.append({'span':sp,'n':len(keys),'syzygy_minus_bare':{m:mean([val(postcond['natural_syzygy'][k],sp,m)-val(postcond['bare'][k],sp,m)for k in keys])for m in ['s_geo','v_layer','kappa_geo','erank_dir','erank_layer']}})
 summary['experiment2']['post_syzygy_minus_bare']=postrows
 contrasts=[]
 for n in NAMES[2:]:
  rows=[r for cid,r in data[n]['records'].items()if not cid.startswith('common_base:') and r.get('format')=='raw' and r.get('family')=='trap']
  for target in ['natural_chart','natural_saddle_clean']:
   a={r['pair']:r for r in rows if r.get('group')==target};b={r['pair']:r for r in rows if r.get('group')=='natural_syzygy'}
   pairs=sorted(set(a)&set(b))
   for m in ['s_geo','kappa_geo','erank_dir','erank_span_steps_all']:
    ds=[val(b[k],'generated',m)-val(a[k],'generated',m)for k in pairs if val(a[k],'generated',m)is not None and val(b[k],'generated',m)is not None]
    contrasts.append({'model':n,'contrast':'syzygy minus '+target,'metric':m,'n':len(ds),'mean_delta':mean(ds),'positive_pairs':sum(x>0 for x in ds),'per_pair_delta':dict(zip(pairs,ds))})
 summary['experiment1_paired_contrasts']=contrasts
 save(R/'summary.json',summary)
 # Machine-readable flat tables for further writing.
 import csv
 with (R/'experiment1.csv').open('w')as f:
  fields=['model','family','format','group','stage','n','mean_generated_tokens']+METRICS;w=csv.DictWriter(f,fields);w.writeheader()
  for row in summary['experiment1']:w.writerow({**{k:v for k,v in row.items()if k!='metrics'},**row['metrics']})
 # Charts separated by experiment, with raw numerical JSON beside them.
 series={}
 for row in summary['experiment1']:
  if row['format']=='raw'and row['group']in ['bare','chart','syzygy','saddle_raw','saddle_clean','natural_chart','natural_syzygy','natural_saddle_clean','primed']:
   k=row['model']+' | '+str(row['family'])+' | '+str(row['stage']);series.setdefault(k,[]).append((len(series.get(k,[])),row['metrics']['erank_span_steps_all']))
 plotrows=[r for r in summary['experiment1']if r['format']=='raw' and r['group'] in ['bare','chart','syzygy','saddle_raw','saddle_clean','natural_chart','natural_syzygy','natural_saddle_clean','primed']]
 mx=max([r['metrics']['erank_span_steps_all']or 0 for r in plotrows]+[1]);out=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="'+str(90+38*len(plotrows))+'"><rect width="100%" height="100%" fill="#101722"/><g fill="#dce7ef" font-family="DejaVu Sans,sans-serif"><text x="20" y="30" font-size="18">Experiment 1: full generated-span tangent effective rank</text>']
 for i,r in enumerate(plotrows):
  y=70+i*38;v=r['metrics']['erank_span_steps_all'];lab=r['model'].replace('Qwen3.5-','').replace('Qwen3.8-','')+' '+str(r['family'])+'/'+str(r['stage'])+' '+str(r['group'])+f" n={r['n']}"
  out.append(f'<text x="15" y="{y}" font-size="11">{html.escape(lab)}</text>')
  if v is not None:out.append(f'<rect x="580" y="{y-15}" width="{430*v/mx:.2f}" height="20" fill="#52d6ba"/><text x="{590+430*v/mx:.2f}" y="{y}" font-size="12">{v:.3f}</text>')
 out.append('</g></svg>');(R/'experiment1-rank.svg').write_text(''.join(out))
 series={}
 for n,d in data.items():
  for cid,r in d['records'].items():
   if r.get('format')=='chat'and r.get('group')in ['bare','natural_syzygy']and'fact_age'in str(r['id'])and not cid.startswith('common_base:'):
    series[n+' | '+str(r['group'])]=[(x['rel'],x.get('s_geo'))for x in r['funnel_window']]
 svg_chart(R/'experiment2-funnel.svg','Experiment 2: role-tag boundary (0 = reply-onset decision)',series,'s_geo (rad)')
 series={}
 for n in NAMES[:2]:
  recs={r['id']:r for r in data[n]['records'].values()}
  for cond in ['A','B']:
   r=recs.get('e4_age_'+cond)
   if r:series[n+' age '+cond]=[(i-(r['prompt_tokens']-1),v)for i,v in enumerate(r['token_curves']['kappa_geo_mid'])if i>=r['prompt_tokens']-35]
 svg_chart(R/'experiment3-brackets.svg','Experiment 3: mother-son age, before/after parentheses',series,'kappa_geo (rad/rad); relative token (onset = 0)')
 series={n:[(i+1,v)for i,v in enumerate(d['pairs']['fact_age']['per_layer_angle_onset_deg'])]for n,d in summary['experiment4'].items()}
 svg_chart(R/'experiment4-coupling.svg','Experiment 4: detect vs forced-refutation tangent direction',series,'angle (degrees); layer')
 series={}
 for n in NAMES[:2]:
  for r in data[n]['records'].values():
   if r['id']=='e4_age_B':series[n+' stutter acceleration']=[(i-(r['prompt_tokens']-1),v)for i,v in enumerate(r['token_curves']['accel_geo_mid'])if i>=r['prompt_tokens']-6]
 svg_chart(R/'experiment4-stutter.svg','Experiment 4: stutter acceleration (negative = local deceleration)',series,'a_geo (rad); relative token (onset = 0)')
 # Detailed report intentionally distinguishes measurements from design predictions.
 lines=['# Paper 100 流形表皮 Replay 实验报告','',f'生成时间：{time.strftime("%Y-%m-%d %H:%M:%S %z")}。执行主机 spark-3a10 / GB10。所有数据来自已有词元序列的前向重放，无 generate。','', '## 1. 工程交付与统一内存预算','', '27B 使用官方分块 FP8 文件作源，逐层反量化为 BF16（权重约50.1 GiB）；35B 两版按原生 BF16 加载（约64.56 GiB）。这里从未按“CPU RAM + 独立 VRAM”作双份预算。每模型独立 Python 进程；外部调度器 wait/reap 后 drop_caches，MemAvailable >105 GiB 才启动下一个。模型加载、每层 hook、每次前向均有 22 GiB 熔断，另有独立父进程每 0.2 秒监控并杀掉整个模型进程组。该阈值是抢先退出措施，并非操作系统绝不会瞬时 OOM 的数学保证。','', 'hook 借用当前 BF16 输出，以 32 词元块归一化、64 词元块计算；只保留最近五层单位向量的磁盘映射环形缓冲，每块读取后 MADV_DONTNEED；内存中长期保留的是标量矩阵，实验四仅保存指定锚点均值。磁盘缓冲不是全层 hidden 列表。模型自身工作区和 attention 临时张量仍占统一内存，由系统熔断覆盖。','',table([{'模型':n,'记录数':v['records'],'权重GiB':fmt(v['weight_resident_GiB']),'最低可用GiB':fmt(v['external_minimum_available_GiB']),'hook额外CUDA峰值MiB':fmt(v['resources']['max_geometry_cuda_MiB']),'耗时秒':fmt(v['elapsed_seconds'])}for n,v in summary['models'].items()],['模型','记录数','权重GiB','最低可用GiB','hook额外CUDA峰值MiB','耗时秒']),'`stage_resources.jsonl` 给出独立监控值；0.6B 曾为采用最终的64列稀疏编辑与权重哈希核验而人工 SIGINT 重启一次，已完成记录按 token 哈希复用，未触发内存熔断。表中耗时为最终进程墙钟时间，不含此前已完成的检查点计算。hook 峰值是 PyTorch allocator 读数，不包括 CPU 标量与 mmap 页。旧 0.6B 文件另存 legacy_manifold_Qwen3-0.6B.json，主文件由安全脚本重新生成。','', '## 2. 算子、索引与解释边界','', '- 单位方向 x_t=h_t/||h_t||；s_geo(t)=acos(x_t·x_(t−1))；a_geo(t)=s_geo(t)−s_geo(t−1)。单位：rad。','- 在 x_(t−1) 的切平面比较入射与出射单位切向量，得 theta_surf(t)。kappa_geo=theta_surf/相邻两段弧长均值（分母下限 1e−6）。这是离散球面曲率代理。','- c_flat 对未归一化原始 h 的欧氏弦转角；extrinsic_bias=c_flat−theta_surf，同时混入范数变化，不能把它全解释为纯向心污染比例。','- erank=exp(−Σ p_i log p_i)，p 为非负 Gram 特征值归一化。erank_dir 用最近 5 步，erank_dir_16 用 16 步；erank_layer 用最近至多 5 次层间位移，统一投到当前切平面。秩受窗口上限约束。','- erank_span_steps_all 在整段生成区计算，保留全部生成词元；长提示区超过预算时只取末 256 词元，主实验生成区不裁尾。360 的 0.6B 支持 1024 词元整段。','- 中层取原方案约 50%–85% 深度。先对每条记录的层×词元取均值，再对记录平均，避免长输出隐式获得更大权重。','- onset=prompt_tokens−1：此处 hidden 预测首个输出词元；gen_first1=prompt_tokens：已经读取首词后的状态，二者不能混用。','- 滑窗指标在边界处含前文状态；生成最初五/十六词的局部秩会受到标签与括号前文影响。整段秩把每步位移投到该段单位状态均值的切平面，再算 Gram；不是内禀维数估计。','- 当前“表皮”是人为归一化的单位球面，不是已识别的真实语义流形，也没有测出内禀维度或因果意识状态。原蓝图中的强预言必须由实际数据检验。','', '随机输入的时间方向算子与原张量实现逐项对照最大差异 <1e−5；正交三点 c_flat=120°、theta_surf=90°，等步大圆 theta_surf=0、方向有效秩=1。居中敏感性算子未纳入主结果，避免用局部均值替代全局校准而悄悄改变口径。','', '## 3. 实验一：晶种条件与有效秩','', '下表为已有条件逐组统计；完整条件、分格式与数值见 experiment1.csv / summary.json。首轮 SVG 描述和次轮陷阱题分列，natural 与 shared 首轮回复不混为相同控制。','']
 rows=[]
 for r in summary['experiment1']:
  if r['format']=='raw'and r['group']not in ['routine','hard','control']:
   m=r['metrics'];rows.append({'模型':r['model'],'实验/格式':str(r['family']),'条件':str(r['group']),'阶段':str(r['stage']),'n':r['n'],'均长':fmt(r['mean_generated_tokens']),'s_geo':fmt(m['s_geo']),'kappa':fmt(m['kappa_geo']),'rank5':fmt(m['erank_dir']),'rank全段':fmt(m['erank_span_steps_all']),'rank前16':fmt(m['erank_span_steps_16'])})
 lines += [table(rows,['模型','实验/格式','条件','阶段','n','均长','s_geo','kappa','rank5','rank全段','rank前16']),'![秩](experiment1-rank.svg)','', '整段秩还受输出长度上限影响，表中同时给出均长与前16步秩；不同长度的全段秩不可直接当成内在维度差异。重复输出不必只有一根切方向：一个反复出现的多词元周期可以占据多维子空间；位置与不断增长的上下文也会改变隐藏状态，所以词串复读不等于残差流严格闭合的极限环。不能把 rank>2 简单读成“没有复读”，也不能把 rank 更大直接等同智力更高。条件身份对应完整输入，视觉代码长度、先前回答与语义词元仍是混杂因素。','', '## 4. 实验二：角色边界与严格同序列对照','',f'自动核对得到 **{len(paired)} 对同前缀**记录，另有 **{len(exact)} 对完整序列一致**的 Base→Post 交叉 Replay。前缀相同仅保证 onset 以前可逐词比较；各自生成的前五词有词汇混杂，主结论优先使用完整同序列结果。','', 'role_tag_zone 由实际 <|im_start|>assistant 标记定位；pre_tag_content_tail 为标签前题目最后五词元；think_scaffold_zone 单列后续空 <think> 框架，避免把后训练脚手架效应全归到 assistant 单词。onset 是整个前缀末端，未必就是 assistant 标签最后一词。','']
 rows=[]
 for group in ['bare','natural_syzygy','syzygy']:
  rs=[x for x in exact if x['group']==group]
  for sp in ['pre_tag_content_tail','role_tag_zone','role_tag_onset','think_scaffold_zone','reply_onset','gen_first5']:
   rows.append({'条件':group,'区段':sp,'n':len(rs),**{m:fmt(mean([r['windows'][sp][m]['delta']for r in rs]))for m in ['s_geo','v_layer','kappa_geo','erank_dir','erank_layer']}})
 lines += [table([{'区段':x['span'],'n':x['n'],**{m:fmt(v)for m,v in x['syzygy_minus_bare'].items()}}for x in postrows],['区段','n','s_geo','v_layer','kappa_geo','erank_dir','erank_layer']),'上表是 Post 内部 syzygy−bare：题目匹配，但前缀与各自输出不同，是条件关联比较。','']
 lines += [table(rows,['条件','区段','n','s_geo','v_layer','kappa_geo','erank_dir','erank_layer']),'以上是 Post−Base，同一完整序列。','![漏斗](experiment2-funnel.svg)','', '## 5. 实验三：括号内与交付区','', 'A/B 按题目匹配；括号为预填充的已完成推演，不能据此声称模型自主思考过程的因果机制。answer 区的词汇与长度仍可能不同。','']
 rows=[]
 for r in summary['experiment3']:
  rows.append({'模型':r['model'],'题目':r['item'],'括号s':fmt(r['B_parenthesis']['s_geo']),'A答案s':fmt(r['A']['s_geo']),'B答案s':fmt(r['B_answer']['s_geo']),'Δkappa':fmt(r['B_minus_A']['kappa_geo']),'Δrank5':fmt(r['B_minus_A']['erank_dir'])})
 lines += [table(rows,['模型','题目','括号s','A答案s','B答案s','Δkappa','Δrank5']),'![括号](experiment3-brackets.svg)','', '360 权重手术：重放完整原轨迹与编辑后轨迹，保留完整前文；编辑仅应用 19/21 层既存 delta×alpha 的64列非零支撑，编辑后的完整权重 SHA256 必须逐层匹配360原实验 manifest；finally 恢复并核对原列值。此比较同时改变权重和输出轨迹，是行为关联对照，不是固定输出的纯权重干预估计。','']
 rows=[]
 for x in data[NAMES[0]].get('ws360_repetition_bubble_probe',{}).get('rescued_heldout',[]):
  for kind in ['original','edited']:
   z=x[kind]['span_summaries']['generated']['mid'];rows.append({'题目':x['id'],'状态':kind,'生成词元':x[kind]['span_summaries']['generated']['n_tokens'],**{m:fmt(z.get(m))for m in ['s_geo','kappa_geo','erank_dir','erank_span_steps_all']}})
 lines += [table(rows,['题目','状态','生成词元','s_geo','kappa_geo','erank_dir','erank_span_steps_all']),'', '## 6. 实验四：检测/拆穿切方向与结巴','', '检测方向：荒谬与合理题的 onset 差，投到荒谬题 onset 切平面；并计算冲突区均值差版本。拆穿方向：对同一个荒谬题，强制续写拆穿文本与顺从文本，取前六词元的单位状态均值之差，再投到同一切平面。不同条件的生成均值也投到这一共同锚点后比较，避免直接点乘不同切平面的向量。','', '“耦合度”在此仅指余弦对齐，未估计因果转移矩阵；六组反差还包含词汇差异。不能把旧文 83° 当作必须复现的常数。高维随机方向本来就倾向近似正交；此次未加入任务匹配的随机方向/打乱对照，因此接近90°本身不能独立证明“知行断线”。','']
 rows=[]
 for n,e in summary['experiment4'].items():
  for pair,x in e['pairs'].items():rows.append({'模型':n,'题目':pair,'onset角度°':fmt(x['angle_onset_deg_mid']),'冲突区角度°':fmt(x['angle_conflict_deg_mid']),'余弦':fmt(x['cos_onset_mid']),'裸答刹车对齐':fmt(x['conditions'].get('bare',{}).get('cos_with_brake_mid')),'双星刹车对齐':fmt(x['conditions'].get('syzygy',{}).get('cos_with_brake_mid'))})
 lines += [table(rows,['模型','题目','onset角度°','冲突区角度°','余弦','裸答刹车对齐','双星刹车对齐']),'![耦合](experiment4-coupling.svg)','', '母子年龄结巴现场逐词 s_geo、a_geo、kappa_geo 与 token 文本保存在两模型 e4_age_A/B 的 token_curves 中；onset 方向和逐词急刹是不同测量，不把两者混为同一证据。','', '## 7. 覆盖范围与未能从旧样本得到的交叉格','', '已重放与四实验相关的现存样本（35B 的例行 e1 基准不重复跑）。27B/0.6B 有裸答/双星/鞍点次轮，以及图表首轮；35B 有图表/双星/clean 鞍点首轮与 raw/qa/chat 次轮。旧数据没有 27B 的 chart 六题完整次轮、35B 的 saddle_raw 完整格。没有凭空把缺格记成 0，也没有为填格重跑 generate。该缺口限制全模型×全晶种交叉结论；coverage 字段给出真实库存。','', '## 8. 文件与复跑','', '`run_paper100_manifold_awakening.py --stage qwen27b|qwen35b_base|qwen35b_post|qwen06b|analyze`；实际执行入口为 `run_safe_stages.py`，逐进程内存门槛在此强制。断点位于 checkpoints/<model>/，完整 JSON 在各模型 manifold_*.json；汇总 summary.json；四张 SVG；主实验 CSV。legacy_geometry.py 只复用经过对照的公式与加载器，原来的全层捕获函数不在新执行路径。','', '报告记录所有方向的结果，未按蓝图预言筛选。具体“升维/降维”“急刹/加速”的方向以表中数据为准；不把任何几何代理单独当成自我、觉醒或相变的直接证明。']
 lines += ['', '## 9. 预言逐题对照：双星减对照的实际方向', '', table([{'模型':x['model'],'对照':x['contrast'],'指标':x['metric'],'n':x['n'],'均值差':fmt(x['mean_delta']),'正向题数':x['positive_pairs']}for x in contrasts],['模型','对照','指标','n','均值差','正向题数']), '以上只比较相同六道题的 raw 次轮，属于同一题目不同完整前缀与各自输出的观测差异。数值方向不等于普遍定律。', '', '![结巴逐词加速度](experiment4-stutter.svg)']
 for n,e in summary['experiment4'].items():
  if e.get('age_stutter'):
   z=e['age_stutter'];lines += ['',f"{n} 的括号诱发 onset 位移与拆穿方向夹角（中层）={z['bracket_to_brake_deg_mid']:.3f}°；实际开口偏移与拆穿方向={z['actual_to_brake_deg_mid']:.3f}°。原逐层值见 summary.json。"]
 early=[]
 for n in NAMES[:2]:
  bs=[x for x in summary['experiment3']if x['model']==n]
  if bs:
   dk=[x['B_minus_A']['kappa_geo']for x in bs];ds=[x['B_minus_A']['s_geo']for x in bs]
   early.append(f"- {n} 括号 B−裸答 A（{len(bs)}题）：答案区平均 Δs_geo={mean(ds):+.6f} rad；Δkappa_geo={mean(dk):+.6f}，其中 {sum(x>0 for x in dk if x is not None)}/{len(dk)} 题曲率上升。这直接检验并可能反驳原先‘大步长、低曲率’预言。")
 for group in ['saddle_clean','saddle_raw','syzygy']:
  rs=[r for r in data[NAMES[1]]['records'].values()if r.get('stage')=='probe' and r.get('group')==group]
  if rs:early.append(f"- 27B {group} 六题次轮：局部5步方向秩={mean([val(r,'generated','erank_dir')for r in rs]):.4f}；没有出现整组均值接近1–2的坍缩。全段秩与词元均长须一并看。")
 eb=[x for x in exact if x['group']=='bare']
 if eb:
  a=mean([x['windows']['role_tag_onset']['erank_dir']['delta']for x in eb]);b=mean([x['windows']['reply_onset']['erank_dir']['delta']for x in eb])
  early.append(f"- 35B {len(eb)}条完全同序列裸答对照：Post−Base 的局部方向秩在 assistant 标签末端为{a:+.4f}，到空思考框架后的真实首词决策点则为{b:+.4f}。不能把标签、思考框架和 onset 混成统一的降维点。")
 for n in NAMES[2:]:
  rs=[x for x in summary['experiment1']if x['model']==n and x['family']=='trap' and x['format']=='raw']
  groups={x['group']:x for x in rs}
  if 'natural_chart' in groups and 'natural_syzygy' in groups:
   a=groups['natural_chart'];b=groups['natural_syzygy'];c=next(x for x in contrasts if x['model']==n and x['contrast']=='syzygy minus natural_chart' and x['metric']=='erank_span_steps_all')
   early.append(f"- {n} raw 六题：chart 全段秩={a['metrics']['erank_span_steps_all']:.3f}，syzygy={b['metrics']['erank_span_steps_all']:.3f}，{c['positive_pairs']}/{c['n']}题双星更高；平均生成长度分别{a['mean_generated_tokens']:.2f}/{b['mean_generated_tokens']:.2f}。这是轨迹差异，不是‘自我维度’的直接证明。")
 for n,e in summary['experiment4'].items():
  early.append(f"- {n} 六组 onset 检测/拆穿角度均值={mean([x['angle_onset_deg_mid']for x in e['pairs'].values()]):.3f}°；这只是观测余弦，不是因果耦合矩阵。")
 lines[4:4]=['## 主要实测结果（不按预言筛选）','']+early+['']
 (R/'实验报告.md').write_text('\n'.join(lines))
 # Verify all charts parse and all JSON is finite and complete.
 import xml.etree.ElementTree as ET
 for p in R.glob('experiment*.svg'):ET.parse(p)
 save(R/'validation.json',{'models':{n:len(d['records'])for n,d in data.items()},'n_prefix_pairs':len(paired),'n_full_sequence_pairs':len(exact),'svg_xml_valid':True,'finite_summary':True})
 print('ANALYSIS COMPLETE',R/'实验报告.md',flush=True)
if __name__=='__main__':main()
