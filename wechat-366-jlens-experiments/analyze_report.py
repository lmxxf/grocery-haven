"""CPU-only summarization and white-background scientific SVGs."""
import json,re,time,math,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
R=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'WenQuanYi Micro Hei','svg.fonttype':'none','figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white','axes.unicode_minus':False})
def read(n):return json.loads((R/n).read_text())
e1,e2,e3,e4=[read(f'experiment{i}.json')for i in range(1,5)]
check=read('experiment4_dosecheck.json')if(R/'experiment4_dosecheck.json').exists()else{}
patch=read('arithmetic_position_check.json')if(R/'arithmetic_position_check.json').exists()else{}

def best(case,stage,pos,value):
 values=[]
 for l,layer in e1['stages'][stage].items():
  for alias,rank in layer[case['name']][pos]['alias_ranks'][value].items():values.append((rank,int(l),alias))
 return min(values)if values else None

def seqbest(case,stage,pos,value):return min((layer[case['name']][pos]['two_digit_00_99'][value]['rank'],int(l))for l,layer in e1['stages'][stage].items())

def spanclass(gen,case):
 s=re.split(r'\n(?:Question:|Q:|问题[:：]|用户[:：]|常识[:：])',gen['text'],maxsplit=1)[0].strip()
 if case.get('numeric'):
  m=re.search(r'[-+]?\d+',s)
  if m:answer=m.group()
  else:
   m=re.search('十二|八|六',s);answer={'十二':'12','八':'8','六':'6'}.get(m.group())if m else None
  return {'answer_span':s,'answer':answer,'old':answer in case['old_aliases'],'new':answer in case['new_aliases']}
 a=any(w.lower()in s.lower()for w in case['old_aliases']);b=any(w.lower()in s.lower()for w in case['new_aliases'])
 return {'answer_span':s,'old':a and not b,'new':b and not a,'ambiguous':a==b}

summary={'complete':True,'experiment1':[],'experiment2':{},'experiment3':{},'experiment4':{},'raw_files':[f'experiment{i}.json'for i in range(1,5)],'method_notes':['One model, all GPU calls on spark-3a10.','Raw vocabulary rank and two-digit candidate-set rank are distinct.','Greedy one completion per condition; flip percentages are fractions of six cases, not repeated-sampling probabilities.']}
for case in e1['cases']:
 rec={'name':case['name'],'prompt':case['prompt'],'tokens':case['tokens'],'anchors':case['anchors'],'stages':{}}
 for stage in ['vanilla','n1','n100']:
  entry={}
  for label,p in [('operand',case['anchors']['second_operand']),('plus',case['anchors']['plus']),('last',len(case['tokens'])-1)]:
   entry[label]={'intermediate_single_token_alias_best':best(case,stage,p,case['intermediate']),'answer_single_token_alias_best':best(case,stage,p,case['answer'])}
   if case['conditional_rows']:entry[label].update(intermediate_two_digit_rank=seqbest(case,stage,p,case['intermediate']),answer_two_digit_rank=seqbest(case,stage,p,case['answer']))
  rec['stages'][stage]=entry
 summary['experiment1'].append(rec)

rates={g:{'new_count':0,'baseline_old_count':0,'rescues_from_old':0,'cases':[]}for g in ['english','chinese','both','random']}
for q in e2['results']:
 base=spanclass(q['baseline_generation'],q['case']);q['answer_span_baseline']=base
 for a in q['conditions']:
  if 'generation'not in a:continue
  label=a['group'];cls=spanclass(a['generation'],q['case']);a['answer_span_class']=cls
  rates[label]['new_count']+=int(cls['new']);rates[label]['baseline_old_count']+=int(base['old']);rates[label]['rescues_from_old']+=int(cls['new']and base['old']);rates[label]['cases'].append({'case':q['case']['name'],'classification':cls})
for v in rates.values():v['new_fraction_all_cases']=v['new_count']/len(e2['results']);v['flip_fraction_baseline_old']=v['rescues_from_old']/v['baseline_old_count']if v['baseline_old_count']else None
summary['experiment2']={'groups':rates,'classification':'first answer passage, cut before explicit new question/round; Chinese 八/六/十二 normalized; mixed old/new is ambiguous','note':'All source strings and original first-line classification retained in experiment2.json; no new model generation for rescoring.'}
(R/'experiment2_annotated.json').write_text(json.dumps(e2,ensure_ascii=False,indent=2))
summary['experiment3']={'broadcast':[],'selectivity':[]}
for q in e3['broadcast']:
 aliases={'currency':(['欧元','euro'],['日元','yen']),'capital':(['罗马','rome'],['东京','tokyo']),'language':(['意大利语','italian'],['日语','japanese'])}[q['name']]
 case={'old_aliases':aliases[0],'new_aliases':aliases[1]};row={'name':q['name'],'baseline':spanclass(q['baseline_generation'],case),'conditions':{}}
 for a in q['conditions']:
  if 'generation'in a:row['conditions'][a['kind']]=spanclass(a['generation'],case)
 summary['experiment3']['broadcast'].append(row)
for q in e3['selectivity']:
 summary['experiment3']['selectivity'].append({'task':q['task'],'swap_generation_equals_baseline':next(a['generation']['token_ids']for a in q['conditions']if a['kind']=='swap'and a['alpha']==1)==q['baseline_generation']['token_ids'],'random_generation_equals_baseline':next(a['generation']['token_ids']for a in q['conditions']if a['kind']=='random'and a['alpha']==1)==q['baseline_generation']['token_ids']})
summary['experiment4']={'primary_target_mentions':sum(x['analysis']['named_concept']for x in e4['runs']if x['kind']=='concept'),'primary_semantic_runs':sum(x['kind']=='concept'for x in e4['runs']),'primary_self_report_hits':sum(x['analysis']['elicited_self_report_phrase']for x in e4['runs']if x['kind']=='concept'),'baseline_uninjected_text':e4['baseline_generation']['text'],'hook_sanity':check,'arithmetic_position_followup':patch}
(R/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))

# Figure 1: concrete token-position heatmaps, same exact digit targets.
case=e1['cases'][0];fig,axes=plt.subplots(2,2,figsize=(11,8),sharex=True,sharey=True)
for row,stage in enumerate(['vanilla','n100']):
 for col,value in enumerate(['6','8']):
  z=np.array([[e1['stages'][stage][str(l)][case['name']][p]['alias_ranks'][value][value]for p in range(len(case['tokens']))]for l in range(64)])
  image=axes[row,col].imshow(z,aspect='auto',origin='lower',norm=LogNorm(1,248320),cmap='Blues_r');axes[row,col].set(title=f'{stage}：数字 {value}',ylabel='层号（0起）');axes[row,col].set_xticks(range(len(case['tokens'])),[repr(t)for t in case['tokens']])
fig.suptitle('2*3+2=：同一个数字的Rank依赖层和位置',fontsize=15);fig.colorbar(image,ax=axes.ravel().tolist(),label='词表Rank（越小越前）',shrink=.75);fig.savefig(R/'arithmetic_token_heatmap.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(11,4.5));x=np.arange(6);w=.24
for j,(stage,label)in enumerate([('vanilla','Vanilla'),('n1','N=1'),('n100','N=100')]):
 vals=[best(c,stage,len(c['tokens'])-1,'6')[0]for c in e1['cases'][:6]];bars=ax.bar(x+(j-1)*w,vals,w,label=label);ax.bar_label(bars,fmt='%d',fontsize=8)
ax.set_yscale('log');ax.set_ylim(.8,180);ax.set_xticks(x,['紧凑算式','空格算式','Fact前缀','英文单词','中文+数字','中文汉字']);ax.set_ylabel('末位置跨层最好Rank（6/six/六等单token别名）');ax.legend();ax.set_title('只改题面格式，N=100也不保证中间值排第1');fig.tight_layout();fig.savefig(R/'arithmetic_formats.svg');plt.close(fig)

fig,ax=plt.subplots(figsize=(11,4.7));x=np.arange(len(e2['results']));w=.19
for j,(group,label)in enumerate([('english','英文'),('chinese','中文'),('both','中英共同'),('random','随机（匹配共同组）')]):
 vals=[]
 for q in e2['results']:
  a=next(a for a in q['conditions']if a['group']==group and a['alpha']==1 and(group!='random'or a['matched_to']=='both'))
  vals.append(a['new_minus_old_sequence_logprob']-q['baseline']['new_minus_old_sequence_logprob'])
 ax.bar(x+(j-1.5)*w,vals,w,label=label)
ax.axhline(0,c='gray',lw=.8);ax.set_xticks(x,[q['case']['name']for q in e2['results']],rotation=15);ax.set_ylabel('Δ[log p(新答案串) − log p(旧答案串)]');ax.set_title('换心：局部成功与失败都保留（α=1）');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(R/'swap_effects.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.4));x=np.arange(3)
for j,(kind,label)in enumerate([('swap','同一处写入'),('random','等范数随机')]):
 v=[]
 for q in e3['broadcast']:
  a=next(a for a in q['conditions']if a['kind']==kind and a['alpha']==1);v.append(a['new_minus_old_sequence_logprob']-q['baseline']['new_minus_old_sequence_logprob'])
 ax.bar(x+(j-.5)*.3,v,.3,label=label)
ax.axhline(0,c='gray',lw=.8);ax.set_xticks(x,['货币','首都','官方语言']);ax.set_ylabel('新/旧答案串log概率差的变化');ax.set_title('单层、单位置、固定同一增量：本次未观察到三路翻转');ax.legend();fig.tight_layout();fig.savefig(R/'broadcast_effects.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(9,3.8));z=np.array([[int(next(a for a in e4['runs']if a['concept']==name and a['kind']=='concept'and a['alpha']==v)['analysis']['named_concept'])for v in [.05,.1,.2]]for name in ['bread','hotpot','elephant']]);ax.imshow(z,cmap='Blues',vmin=0,vmax=1,aspect='auto');ax.set_xticks(range(3),['α=0.05','α=0.10','α=0.20']);ax.set_yticks(range(3),['面包 / bread','火锅','大象'])
for i in range(3):
 for j in range(3):ax.text(j,i,'未提及'if z[i,j]==0 else'命中',ha='center',va='center')
ax.set_title('单位置概念脉冲：主剂量区间9次均未报告目标概念');fig.text(.5,.01,'无注入时已自述“量子纠缠”；这类报告不能单独作为感知注入的证据。',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(R/'introspection_results.svg');plt.close(fig)

lines=['# 366期：Qwen3.8-27B J-lens 前向与干预实验报告','',f'生成时间：{time.strftime("%Y-%m-%d %H:%M:%S %z")}。GPU计算仅在spark-3a10 / GB10；本机只作CPU整理。','', '## 核心结果','',
'1. 网友现象不是一个对所有格式、模型、镜头都必然成立的定律。紧凑`2*3+2=`在Vanilla末位置L55可读到数字6的Rank1，L59才出现数字8的Rank1；N=100里6最好Rank2（L56），加入空格后其最好单token别名Rank变成11。',
'2. 靴子国英文题在L34..44的语义坐标换心能把欧元改为日元，匹配随机对照仍是欧元；同一窗口的中文题、蜘蛛和算术没有得到同样普遍的成功。',
'3. 单层L38、共享主体末位置只写一次的广播测试没有三路翻转；不能拿多层多位置反复钳位的结果冒充一次写入广播。',
'4. 无注入基线就自述突然想到“量子纠缠”；主剂量0.05/0.10/0.20均未报告实际注入概念。强单脉冲补测及hook核验见后文。','',
'## 环境、方向与护栏','',
'沿用365的meta骨架+逐shard safe_open CUDA读取+128×128 FP8 block原地反量化BF16+逐shard清缓存+重建rotary_emb。原模型参数不改，不运行模型梯度。启动可用内存>100GiB；进程内每0.25秒低于22GiB自退；独立父进程每0.25秒低于20GiB杀整个模型进程组。完整运行和补测日志、watchdog.json均归档。',
'读取层号0..63均指block输出，最后RMSNorm之前；不要把不同API是否包含embedding的hidden_states元组索引直接当同一层号。所有J-lens实际读出都经过完整Final RMSNorm与lm_head。',
'按需构建词元方向，未物化每层整个248320×5120字典：v_l(t)=J_lᵀ·diag(FinalRMSNorm.weight)·lm_head.weight[t]。v_l(t)·h给出最终归一化RMS公共分母之前的logit分子，理想实数运算下公共正分母不改变词表排序；它不是包含样本依赖径向项的完整概率梯度。方向和token IDs见concept_directions.pt及experiment1.json。',
'坐标Swap采用给定方向列V、干净前向坐标c=Vᵀh_clean，交换指定两词坐标得到c_swap，再用V(VᵀV+λI)⁻¹对当前残差作最小范数修正；λ=1e−6·mean(diag(VᵀV))。这是小Gram矩阵的稳定化求解，不是求5120维J的普通逆。α插值目标坐标；每位置增量上限为干净残差L2的25%，故达到上限时不再是精确坐标交换。',
'随机方向正交于同层的四个英中词元方向。按每次语义干预的实际逐位置增量范数匹配，BF16再次舍入可有微小差异；主图的随机组匹配双语组，JSON另含匹配英/中各组的随机对照。不能仅凭不同语言组幅度差异宣布中文/英文机制更强。','',
'## 实验1：九种格式、每个token、64层','',
'所有题都保留逐位置Top-5及可单token表达的数字/英文数词/中文数词Rank。56、42等不是词表中的单token，本模型将数字逐位切开；不把5的Rank叫作56的Rank。',
'两位数另作严格条件评分：S_l(ab)=log p_l(a|prefix)+log p_l(b|prefix+a)，枚举相同长度的00..99共100个候选排名。每个原始前缀都对0..9第一位各做一次教师强制前向，未向模型喂入目标第二位。这个候选集Rank不是248320词表Rank，也不直接证明完整数值概念已经作为单个内部变量存在；低层还可能反映数字搭配频率。','',
'|题面|镜头|乘数位置：中间值最好Rank|加号位置|末位置|末位置终值|','|---|---|---:|---:|---:|---:|']
for q in summary['experiment1']:
 for stage,s in q['stages'].items():
  multi='intermediate_two_digit_rank'in s['last']
  def value(pos,answer=False):
   k=('answer_'if answer else'intermediate_')+('two_digit_rank'if multi else'single_token_alias_best');v=s[pos][k];return str(v[0])+f' (L{v[1]})'if v else'无单token别名'
  lines.append(f"|{q['name']}|{stage}|{value('operand')}|{value('plus')}|{value('last')}|{value('last',True)}|")
lines += ['', '表中前六题为数字/数词别名的词表最好Rank，后三题为00..99候选串最好Rank，两种尺度不可直接比较。完整每层每位置结果见experiment1.json，字符偏移和操作数/加号锚点也已保存。',
'纸面版本的另一个区别：原论文明确展示了Opus 4.5的多步算式21→42→49及逐位置热图，不是保证任意Qwen提示都出现同一轨迹。参考：[原论文](https://transformer-circuits.pub/2026/workspace/index.html)。本次发现格式、词元写法、镜头、层号和观察位置都影响显影；既有Vanilla已显影的反例，也有N=100仍不排第1的情况。',
'关于“早在3处计算好，再用KV cache”：此处用完整前缀forward与causal位置读数，没有对KV缓存作消融；48个线性注意力层还会传递递归状态。前面可读/不可读都不能单独证明缓存复用或排除其他通路。不能把prefill的位置轴直接当逐字阅读的物理时间轴。',
'', '## 实验2：英/中/双语Swap与匹配随机','',
'六题分别为英/中靴子货币、东京货币、英/中蜘蛛腿、2*3+2。窗口L34..44，原始prompt全部位置钳位，生成的新token不再编辑；剂量α=0.5/1/2。greedy生成32 tokens，可能含原模型续写新问题或截断，原文和hit_limit均保留。',
'6→10的方向用可单token化的six→ten与六→十；逻辑预期是10+2=12，不是8→6。直接把56当一个词元做Swap没有实施，因为词表中不存在这样的单token；两位数已在实验1用序列评分处理。',
'翻转率以α=1的六个问题为分母，不是反复采样成功概率。为处理中文开头只有“？”的情况，补做首个回答段评分：截到显式下一轮问题之前，中文八/六/十二归一化；出现新旧答案混合则标不明确。原始first-line判定与生成全部保留，见experiment2_annotated.json。','',
'|方向|新答案题数/6|基线旧答案正确题数|旧→新翻转数|','|---|---:|---:|---:|']
for group,v in rates.items():lines.append(f"|{group}|{v['new_count']}/6|{v['baseline_old_count']}|{v['rescues_from_old']}|")
for q in e2['results']:
 lines+=['',f"### {q['case']['name']}",'',f"题面：{q['case']['prompt']}",f"基线：{q['baseline_generation']['text']!r}"]
 for a in q['conditions']:
  if 'generation'in a:lines.append(f"- {a['group']} α=1：{a['generation']['text']!r}")
lines += ['', '同一英文靴子题的双语Swap校准对照中，Vanilla和N=1仍生成the euro，N=100生成the yen；仅是这一题、α=1和既定窗口下的对照。其余干预以N=100为主，不声称完成所有实验的镜头×剂量×题目全笛卡尔积。完整对照见该题calibration_controls。正向干预胜过随机只支持这个方向/窗口在这个任务有因果作用，不证明全模型的自我意识或J-space普遍优越。',
'', '## 实验3：单处写入广播与任务选择性','',
'共享前缀是“对象：形状像一只靴子的欧洲国家。\\n”，仅在L38共享前缀最后token写入一次，三道下游问题使用同一个增量。三个后缀都严格核对共享token IDs。由于不同长度BF16前向的数值实现，锚点激活最大绝对差可达0.1875；不宣称实际浮点激活逐bit完全一致，但预设FP32增量严格复用；实际BF16写回仍可能有舍入差异。',
'此设置没有得到三路同时变成日元/东京/日语。语言问题的无干预基线本来就错答英语/伦敦，不能把它算作从正确意大利语出发的换心失败。后续需要区分单位置脉冲、问题格式与多层全位置钳位，不能把本次单处失败写成广播机制不存在。',
'法语刺激token IDs在两种任务间完全相同；使用同一个L38单位置固定增量，比较直接续写和中文询问语种。两种任务下α=1的语义及随机生成均与各自基线完全相同。直接续写基线自身重复法语句子；询问语种则答法语。语种名的logit变化是辅助诊断，不是续写语言的准确率。原文见experiment3.json。',
'', '## 实验4：注入与“自述”的脱钩','',
'明确记录提示词：'+e4['prompt'],
'模型被允许报告一个与任务无关的概念，但提示里没有面包、火锅或大象。故是被询问的自我报告测试，不能称完全自发内省。使用chat template并关闭thinking。主实验只在L38最后prompt位置注入一次，δ=α·||h_clean||·单位方向，α=0.05/0.10/0.20；面包方向合并了EN bread与中文面包的单位方向。',
'无注入基线：'+repr(e4['baseline_generation']['text']),
'主实验9次目标概念注入均未提到目标词，也未命中目标相关自述；匹配随机以及N=1/Vanilla面包对照同样保留。无注入也自述“量子纠缠”说明，单凭这样的口头内省不能证明真实检测到了实验者注入。','']
if check:
 lines += ['### Hook生效与有限强剂量核验','','|种类|α|实际L38相对变化|L39变化/原L38长度|max下一词logit变化|提到面包|','|---|---:|---:|---:|---:|---|']
 for q in check['runs']:lines.append(f"|{q['kind']}|{q['alpha']}|{q['observed_relative_change_L38']:.5f}|{q['observed_relative_change_L39']:.5f}|{q['next_logits_max_abs_change']:.5f}|{q.get('mentions_bread','未生成')}|")
 lines += ['', '强剂量仅补测面包的单位置脉冲α=0.5与1.0，附匹配随机；该随机向量只对面包方向正交，主试随机向量则对三个目标方向的张成空间正交。观测到块输出和下一层变化，排除了“hook没生效”的解释；最大logit变化并非零，不能说模型丝毫未受影响。是否检测到概念必须看目标内容，不能把措辞变化或任意突发概念自述算命中。']
if patch:
 lines+=['','## 算术定位补测（探索性）','',patch['definition'],'','|设置|种类|α|新答案6的首词Rank|生成首段|','|---|---|---:|---:|---|']
 for q in patch['runs']:
  if 'generation'in q:lines.append(f"|{q['name']}|{q['kind']}|{q['alpha']}|{q['targets']['new']['first_token_rank']}|{q['generation']['text'].splitlines()[0]}|")
 lines+=['','此补测各α=1设置和随机对照的首个生成答案仍为8，未得到预期6。6方向本身还直接对应最终词元6，压低它可能同时压低期待的新答案；不能把这个干预的未命中当作“从未计算过6”的证明。此补测由实验1观察到L55之后的显影后选定，不能冒称独立预注册验证。它同时使用真实数字6→4（而非six→ten）并换到晚层，不能把与主实验的差异只归因于层号。']
lines += ['', '## 交付文件与边界','',
'`experiment1..4.json`包含全量读数、完整本次生成token片段、干预参数；`concept_directions.pt`为稀疏按需词典；`arithmetic_position_check.json`与`experiment4_dosecheck.json`为明确标注的补核验。`results.json`为整理索引与计数。脚本同目录。',
'五张图均为白底SVG：arithmetic_token_heatmap.svg、arithmetic_formats.svg、swap_effects.svg、broadcast_effects.svg、introspection_results.svg。',
'这些是一个模型、一个检查点、少量固定题目、单次greedy输出下的工程实验。没有以反复调参筛选成功案例替代主结果，没有把输出词元偏移直接解释成主体性或意识。所有反例、未命中、随机对照与截断状态一并归档。']
(R/'实验报告.md').write_text('\n'.join(lines)+'\n')
print('ANALYSIS_AND_REPORT_COMPLETE')
