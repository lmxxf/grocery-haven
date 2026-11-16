import json,math,re
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent
H=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3/experiments/exp1b_archaic_nucai')
def f(x):return 'NA' if x is None else f'{x:.5g}'
def count(m):return '—' if m is None else f"{m['correct']}/{m['n']}"
def save(name,obj):(R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
def find(results,rep):return results[rep['layer']]['references'][rep['name']][rep['method']] if rep['method']!='internal' else results[rep['layer']]['internal'][rep['name']]['top3_delta'][0]
def ref_best(results,name,lo,hi):
 rows=[r for r in results if lo<=r['layer']<=hi]
 def score(r):
  v=r['references'][name]['delta'];return (v['heldout']['correct']/v['heldout']['n'],v['heldout']['d'],v['fit']['delta']) if v['heldout'] else (v['fit']['d'],v['fit']['delta'])
 r=max(rows,key=score);return r['layer'],r['references'][name]['delta']
def selection(results):
 valid=[]
 for r in results:
  if not 10<=r['layer']<=48:continue
  v=r['references']['Moral_Nonliteral']['delta'];h=v['heldout'];b=v['beibi_transfer']
  if h and h['correct']>=3 and b['correct']>=6 and b['delta']>.1:valid.append(r['layer'])
 modes={}
 for wrapper in ['W0','W1','W2','W3a','W3b']:
  vals=[results[l]['references']['Moral_Nonliteral']['delta']['calibration'][wrapper]['normalized_modern_gap'] for l in valid];modes[wrapper]={'n_valid_layers':len(vals),'median_abs_residual':float(np.median(np.abs(vals))) if vals else None,'median_signed_residual':float(np.median(vals)) if vals else None}
 available={'W0':'short','W2':'W2_shared','W3a':'W3'}
 if valid:best=min(available,key=lambda k:modes[k]['median_abs_residual']);best_all=min(modes,key=lambda k:modes[k]['median_abs_residual'])
 else:best='W2';best_all=None
 return dict(valid_layers=valid,calibration=modes,best_calibration_available_for_nucai=best,applied_wrapper=available[best],best_across_all_five=best_all,criterion='L10–L48 synonym-heldout >=3/4, independent modern 卑鄙 >=6/8 and oriented modern gap >0.1; choose minimum median absolute residual; nucai not used',equivalence_tolerance=.1)
def case_rows(samples,probes):
 out=[]
 for s in samples:
  if s['wrapper']=='W2_native' and s['target']=='奴才':
   p=probes[s['id']];out.append(dict(group=s['group'],sample_id=s['sample_id'],source=s['source'],doc_id=s['doc_id'],split=s['split'],left_chars=len(p['text'])-2,left_tail=p['text'][-182:],tokens=p['token_count'],translation=s.get('translation',False)))
 return out

def build(results,readouts,reps,geometry,probes,pairs,samples):
 design=json.loads((R/'design.json').read_text());chosen=selection(results);save('wrapper_selection.json',chosen);w=chosen['applied_wrapper'];cases=case_rows(samples,probes);save('verified_case_index.json',cases)
 lines=['# Exp1B：跨时代语义考古——卑鄙校准与奴才验光','',f"主数据：{len(probes)} 条唯一裸文本；A1/A2/B/C各10处真实目标，另列1处雍正上谕、1处曹寅满文译汉核验样本。所有64层同时采集。正式前向见 `forward_complete.json`；投影/有限数核验见 `validation.json`。",'', '## 先读这些数字','',f"非字面道德轴通过同义词留出与独立‘卑鄙’检验的L10–L48层：{chosen['valid_layers']}。",f"五种卑鄙包裹中总体最低残留：{chosen['best_across_all_five']}；已对奴才执行的严格共享包裹中，选用 {chosen['best_calibration_available_for_nucai']} → {w}。不使用奴才组结果反选去污染包裹。",'', '|参照轴|层/轴|κ|选轴Δ|训练d|同义词留出|现代卑鄙泛化|A1奴才−臣 Δ [95%CI]|A2奴才−我 Δ [95%CI]|','|---|---|---|---|---|---|---|---|---|']
 for rep in reps:
  if rep['method']=='internal':continue
  v=find(results,rep);a=v['cohorts'][w]['A1']['minimal_pairs']['臣'];b=v['cohorts'][w]['A2']['minimal_pairs']['我']
  show=lambda q:f"{f(q['mean'])} [{f(q['ci95'][0])},{f(q['ci95'][1])}]"
  lines.append(f"|{rep['name']}|L{rep['layer']:02d} C{rep['axis']}|{f(v['kurtosis'])}|{f(v['fit']['delta'])}|{f(v['fit']['d'])}|{count(v['heldout'])}|{count(v['beibi_transfer'])}|{show(a)}|{show(b)}|")
 lines+=['','参照轴名表示其选轴对立，不自动保证纯语义含义；下文同时保留真实J词表、语料、跨词泛化和身份轴交叉读数。','', '## 数据与方法','',
'1. 本地Qwen3.8-27B-FP8按v3同一加载器逐块解量化至BF16，一次加载完成所有前向及主J-Lens读出；L45同层补核仅加载归一化/词表输出权重，未再次加载27B或跑探针。无BOS/EOS、无对话模板、无padding，前缀与目标词分别分词后拼接。目标词在输入末尾，主口径为末token，辅口径为词内原残差均值。每层都是block输出resid_post，不是最终归一化输出。',
'2. 投影严格为 `u=h/max(||h||₂,1e-12)`，`z=(u-center) @ reading_matrix.T`。原v3轴号和正负号保留；统计中的正向由外源训练对立决定，词表显影仍按v3原正负两极展示。κ是v3原136.6万词测试集超额峰度。',
'3. 五类外源参照各8对；Moral_Nonliteral、R1各另有4对未参与选轴的词汇留出。每层分别取|平均配对差|与|配对t|最大单轴。d为两组标准差合并后的Cohen d，d_z为配对差标准化效应量，t=d_z√n；5120轴训练名义p另作层内BH校正。参照选轴不读取任何真实奴才样本。',
'4. 内源发现只投影既有v3 ICA，不在小样本池重新拟合ICA。三个预先定义的同目标词对立为A1−C、A2−C、B−A2；仅用fit文档选均值差Top3和t Top1，测试按文档切分。相同回目/文章的重复片段不跨训练和留出。',
'5. 三种严格共享前缀的对应是W0→short、W2→W2_shared、W3a→W3。W2_native另保留各篇原文左侧至多1300字，为原著沉浸读数；不是把三国志替换成红楼梦后宣称仍是同一个控制变量。W1和W3b为校准尺上的长引文补充，不把未执行的包裹伪称已套用于奴才。',
'6. 校准先算每种包裹的 `D_w=z(卑鄙)-mean[z(微贱),z(浅陋),z(愚钝)]`，再除以独立现代参照差 `G=μ_mod(卑鄙)-μ_mod(褒义)`。残留R_w=D_w/G；消除率=100(1−R_w)。另给相对W0消除率100(1−D_w/D_0)。不裁剪负值或超过100%的结果；这些值表示越过参照零点，不是“负污染”或物理概率。',
'7. “归零”采用配对基线和预定等价带：A1比臣、A2比小的/下官/我；当95%文档聚类bootstrap区间整体位于±10%对应外源现代对立差之内，记为接近基线。原始ICA坐标0不是无羞辱的心理学原点。1000次聚类bootstrap固定seed20261116；原始逐样本值和词均值读数全部保留。',
'8. 不把未来文字搬到左边。B的斥责/怒骂在目标前已出现；右侧原文只保存在出处核验记录。杨宗仁022688的奴才在奏首，原折有效左文只有“湖广总督”，从未拼接其右侧正文到前面。网页上一回/回目录/下一回导航已剔除，清理记录单列。','',
'## 真实来源核验','',
'- 《三国志》卷35：维基文库简体正文；删除裴松之小字注，避免注中提前引用同一句。W2从诸葛亮字孔明起至目标，目标前2369 tokens；无前置卑鄙。W1从先帝创业未半起至目标，实际395 tokens，未按约180字的估数删改原文。',
'- 《红楼梦》：维基文库120回全部下载，逐回URL、SHA256、长度见honglou_manifest.json。检出137处奴才，人工依据左文选A2/B各10处；页内导航剔除。A2有些目标靠近章首，实际左文不足1300字时不跨回拼凑，也不拿后文补长度。',
'- 《关于江宁织造曹家档案史料》：下载扫描/转录PDF并用pdftotext提取；剔除页码与广告水印，保留原有异体、括注和用字。A1九份奴才奏文来自此汇编，另加杨宗仁影印一例。曹寅第18号属满文译汉，仅在A1_translation_audit单列，不混入十份主样本。',
'- 杨宗仁：故宫文物月刊321期〈廉洁如冰、耿介如石〉的故宫022688请安折影印，雍正元年四月初五日；人工放大核见黑字奴才与朱改臣、称臣得体。官修硃批谕旨卷4已经转录为臣，未将其臣字伪报为原来的奴才。',
'- 年羹尧/鄂尔泰：已取原奏文有臣，作为original_chen独立对照；没有为了凑作者名单改写成奴才。',
'- 雍正斥责用经核验的《上谕内阁》卷63“此等卑污之习皆始自包衣下贱奴才”；未能核验的“不知好歹之奴才”未用。此条是上谕，不冒称奏折尾朱批。',
'- C取鲁迅《我谈堕民》《漫与》《上海文艺之一瞥》《谚语》《隔膜》共10处；按五篇作品聚类。《灯下漫笔》下载本没有奴才二字，未把网上误引塞进该文。',
'- 345词英文前缀是明示的实验构造文本，不冒充历史引文；只说明文献学阅读场景，没有提前解释卑鄙/奴才词义。现代参考句同样明示为构造控制。','', '|组/样本|回目/文档|split|原文左长|末尾可见左文＋目标|出处|','|---|---|---|---|---|---|']
 for x in cases:
  quote=json.dumps(x['left_tail'],ensure_ascii=False).replace('|','\\|');lines.append(f"|{x['group']}/{x['sample_id']}|{x['doc_id']}|{x['split']}|{x['left_chars']}|{quote}|[原文]({x['source'].replace(' ','%20')})|")
 lines+=['','## 校准尺：五种包裹总体残留','', '|包裹|有效轴层数|残留绝对值中位数|有符号残留中位数|','|---|---|---|---|']
 for name,x in chosen['calibration'].items():lines.append(f"|{name}|{x['n_valid_layers']}|{f(x['median_abs_residual'])}|{f(x['median_signed_residual'])}|")
 lines+=['','## 外源选轴全64层','', 'delta为均值差最大轴；t为配对t最大轴。后续完整读数默认使用delta轴，两者不一致时直接保留，不用高训练t替换留出表现。','']
 for group in ['Mod_Moral_Beibi','Moral_Nonliteral','Status_Humble','R1_Humiliation','R2_Court']:
  lines+=[f'### {group}','', '|L|C_delta|κ|Δfit|d_fit|同义词留出|卑鄙独立对照|C_t|Δfit_t|d_fit_t|t轴留出|均值token选C|','|---|---|---|---|---|---|---|---|---|---|---|---|']
  for r in results:
   v=r['references'][group]['delta'];t=r['references'][group]['t'];lines.append(f"|{r['layer']:02d}|{v['axis']}|{f(v['kurtosis'])}|{f(v['fit']['delta'])}|{f(v['fit']['d'])}|{count(v['heldout'])}|{count(v['beibi_transfer'])}|{t['axis']}|{f(t['fit']['delta'])}|{f(t['fit']['d'])}|{count(t['heldout'])}|{v['mean_token_top1']}|")
  lines.append('')
 lines+=['## 非字面道德轴：各层校准原始值与消除率','', '各格为：原始卑鄙z；同包裹中性均值；匹配差D；现代锚消除%；相对W0消除%。保留原符号定向。','', '|L/C|W0|W1|W2|W3a|W3b|','|---|---|---|---|---|---|']
 for r in results:
  v=r['references']['Moral_Nonliteral']['delta'];cells=[]
  for name in ['W0','W1','W2','W3a','W3b']:
   q=v['calibration'][name];cells.append(';'.join([f(q['raw_beibi']),f(np.mean(list(q['raw_neutrals'].values()))),f(q['matched_delta']),f(q['removal_percent_modern_anchor']),f(q['removal_percent_vs_W0'])]))
  lines.append(f"|{r['layer']:02d}/{v['axis']}|"+'|'.join(cells)+'|')
 lines+=['','## 屈辱轴与朝仪轴：原文各组及最小配对全64层','',f'以下使用由卑鄙独立校准选出的共享包裹 `{w}`。Δ/CI是奴才相对同位置替换词的差；“近零”需要完整区间落入±10%外源对立差，非比较绝对z与0。','']
 for group in ['R1_Humiliation','R2_Court','Moral_Nonliteral','Status_Humble']:
  lines+=[f'### {group}','', '|L/C|A1原始μ|A2原始μ|B原始μ|C原始μ|A1−臣 Δ [CI]|A1近零|A2−我 Δ [CI]|A2近零|A2−小的 Δ|A2−下官 Δ|','|---|---|---|---|---|---|---|---|---|---|---|']
  for r in results:
   v=r['references'][group]['delta'];co=v['cohorts'][w];a=co['A1']['minimal_pairs']['臣'];b=co['A2']['minimal_pairs']['我'];ci=lambda x:f"{f(x['mean'])} [{f(x['ci95'][0])},{f(x['ci95'][1])}]"
   lines.append(f"|{r['layer']:02d}/{v['axis']}|"+'|'.join(f(co[g]['raw']['mean']) for g in ['A1','A2','B','C'])+f"|{ci(a)}|{a['equivalent_within_10pct_modern_gap']}|{ci(b)}|{b['equivalent_within_10pct_modern_gap']}|{f(co['A2']['minimal_pairs']['小的']['mean'])}|{f(co['A2']['minimal_pairs']['下官']['mean'])}|")
  lines.append('')
 lines+=['## 奏折奴才−臣：四种左文包裹的变化','', '|L/R1轴|short Δ|W2_native Δ|W2_shared Δ|W3 Δ|末token与词均值同号（选定包裹）|','|---|---|---|---|---|---|']
 for r in results:
  v=r['references']['R1_Humiliation']['delta'];qs=[v['cohorts'][ww]['A1']['minimal_pairs']['臣'] for ww in ['short','W2_native','W2_shared','W3']];x=v['cohorts'][w]['A1']['minimal_pairs']['臣'];same=x['mean']*x['mean_token']['mean']>0
  lines.append(f"|{r['layer']:02d}/{v['axis']}|"+'|'.join(f(q['mean']) for q in qs)+f'|{same}|')
 lines+=['','## 同为奴才的内源发现与两轴几何','', '|L|A1−C的C/κ|A1−C留出|B−A2的C/κ|B−A2留出|同轴|reading cos|writing cos|样本坐标相关|','|---|---|---|---|---|---|---|---|---|']
 for r,g in zip(results,geometry):
  a=r['internal']['court_vs_modern']['top3_delta'][0];b=r['internal']['insult_vs_routine_HLM']['top3_delta'][0];lines.append(f"|{r['layer']:02d}|{a['axis']}/{f(a['kurtosis'])}|{a['heldout_correct']}/{a['heldout_total']}|{b['axis']}/{f(b['kurtosis'])}|{b['heldout_correct']}/{b['heldout_total']}|{g['same_axis']}|{f(g['reading_cosine'])}|{f(g['writing_cosine'])}|{f(g['observed_score_correlation'])}|")
 lines+=['','## 代表轴：J-Lens完整正负Top25及真实语料','', '外源代表轴各在L10–L20、L24–L48分别按词汇留出表现、再按效应量选出；没有只看深层。R2没有词汇留出，按训练d选取。内源代表轴按原文文档留出表现选取，列明选择规则。每根轴保留自身原始J正负两极；sign说明哪端对应其训练对立。','']
 for rep,rd in zip(reps,readouts):
  l=rep['layer'];c=rep['axis'];v=find(results,rep)
  lines += [f"### {rep['name']}：L{l:02d} C{c}",'',f"κ={f(v['kurtosis'])}；对立方向sign={rep['sign']:+g}；J重算与原profile Top20最大分数差={f(rd['stored_top20_max_score_error'])}。",'', '|排名|原正极：ID / 原词 / score|原负极：ID / 原词 / 原轴score|','|---|---|---|']
  def cell(x):return f"{x['token_id']} / {json.dumps(x['text'],ensure_ascii=False)} / {f(x['score'])}".replace('|','\\|')
  for k,(a,b) in enumerate(zip(rd['positive_top25'],rd['negative_top25'])):lines.append(f'|{k+1}|{cell(a)}|{cell(b)}|')
  lines.append('')
  for side in ['positive','negative']:
   occ=rd['profile']['examples'].get(side,{}).get('occurrences',[]);lines+=[f'**原测试语料 {side}**','']
   if not occ:lines+=['原profile未保存此侧语料；未编造补齐。','']
   for x in occ[:5]:lines.append(f"- z={f(x['score'])}；token={json.dumps(x['text'],ensure_ascii=False)}；{json.dumps(x['context'],ensure_ascii=False)}")
   lines.append('')
  if rep['method']!='internal':
   lines+=['|卑鄙校准|原始z|中性均值|匹配差D|相对现代差R|相对W0消除%|','|---|---|---|---|---|---|']
   for cw,cv in v['calibration'].items():lines.append(f"|{cw}|{f(cv['raw_beibi'])}|{f(np.mean(list(cv['raw_neutrals'].values())))}|{f(cv['matched_delta'])}|{f(cv['normalized_modern_gap'])}|{f(cv['removal_percent_vs_W0'])}|")
   lines.append('')
   lines+=['|组/包裹|原始μ|词均值μ|奴才−臣或我 Δ|95%CI|词均值配对Δ|','|---|---|---|---|---|---|']
   for ww,cohorts in v['cohorts'].items():
    for co,entry in cohorts.items():
     pair=entry['minimal_pairs'].get('臣',entry['minimal_pairs'].get('我'));lines.append(f"|{co}/{ww}|{f(entry['raw']['mean'])}|{f(entry['mean_token_raw']['mean'])}|{f(pair['mean']) if pair else '—'}|{str(pair['ci95']) if pair else '—'}|{f(pair['mean_token']['mean']) if pair else '—'}|")
   lines.append('')
  else:
   lines+=['内源各组均值：`'+json.dumps(v['group_means'],ensure_ascii=False)+'`。','']
 lines+=['## 分词与复现','', '|目标|token IDs|逐token解码|','|---|---|---|']
 for x in json.loads((R/'tokenization.json').read_text()):lines.append(f"|{x['target']}|{x['ids']}|{json.dumps(x['decoded'],ensure_ascii=False)}|")
 lines+=['',f'重数据目录：`{H}`。其中activations_last.npy / activations_mean.npy保存float32原残差，z_last.npy / z_mean.npy保存全轴坐标，all_layers_full.json保存各层完整逐样本统计。轻量目录的representative_raw_scores.json可直接核对每条探针；probes.json含全部输入与token span；source_slice_verification.json仅将右文用于出处核验。','', '复现入口：`bash run_all.sh`。只有前向和J读出加载完整模型，后续报告读取已保存结果即可。实际版本、哈希和进度见design.json、validation.json、run.log。']
 (R/'report_exp1b.md').write_text('\n'.join(lines)+'\n')
 summary=['# ICA-Lens v3 Exp1B','',f'{len(probes)}条裸文本、64层；目标均位于输入末尾。完整报告：[report_exp1b.md](report_exp1b.md)。','',f'独立校准选择：{chosen["best_calibration_available_for_nucai"]} → {w}；可用校准层数 {len(chosen["valid_layers"])}。','', '|参照|L/C|A1奴才−臣|95%CI|A2奴才−我|95%CI|','|---|---|---|---|---|---|']
 for rep in reps:
  if rep['name'] not in ['Moral_Nonliteral','R1_Humiliation','R2_Court']:continue
  v=find(results,rep);a=v['cohorts'][w]['A1']['minimal_pairs']['臣'];b=v['cohorts'][w]['A2']['minimal_pairs']['我'];summary.append(f"|{rep['name']}|{rep['layer']}/{rep['axis']}|{f(a['mean'])}|{a['ci95']}|{f(b['mean'])}|{b['ci95']}|")
 summary+=['','轻量脚本、真实探针、分词、日志、代表轴原始读数均在本目录。',f'大数据只在 `{H}`，不放进grocery-haven。','', '真实来源包括维基文库120回红楼梦、三国志卷35、鲁迅五篇原文、曹家档案汇编、故宫杨宗仁影印与上谕内阁卷63。年羹尧/鄂尔泰已核原文称臣；曹寅满文译汉单列。','', '运行：`bash run_all.sh`。文件说明见完整报告末尾。']
 (R/'README.md').write_text('\n'.join(summary)+'\n');save('report_metadata.json',dict(report_lines=len(lines),wrapper=w,representatives=reps));print('REPORT_WRITTEN',len(lines),w,flush=True)
