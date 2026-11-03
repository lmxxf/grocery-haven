#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,collections,statistics,math
import numpy as np
from transformers import AutoTokenizer
from export_review import build
R=Path(__file__).resolve().parent
build();key=json.loads((R/'review_key.json').read_text());grades=json.loads((R/'grades.json').read_text())['grades'];protocol=json.loads((R/'protocol.json').read_text())
models=protocol['models'];conditions=protocol['conditions'];data=[];audit={'counts':{},'duplicate_age':[],'boundary_inside_think':[]}
constraints={'logic_candle':'其余持续燃烧直到耗尽','logic_age':'35岁','logic_weekday':'早两天','logic_animals':'28条腿','logic_ball':'贵100元'}
for model in models:
 files=sorted((R/'raw'/model).glob('rel_*.json'));assert len(files)==126,(model,len(files));audit['counts'][model]=len(files)
 tok=AutoTokenizer.from_pretrained('/home/lmxxf/work/models/'+model,local_files_only=True)
 fingerprints=set()
 for f in files:
  r=json.loads(f.read_text());spec=r['relation_spec'];q=spec['question'];bid=key['records'][model+'::'+r['id']];assert bid in grades,('UNGRADED',bid)
  assert r['prompt']==spec['prompt'];assert not r['input_special_token_ids'];assert not set(r['token_ids'][:r['prompt_tokens']])&set(tok.all_special_ids)
  assert tok(r['prompt'],add_special_tokens=False).input_ids==r['token_ids'][:r['prompt_tokens']]
  assert len(r['generated_token_ids'])<=160
  fingerprints.add(json.dumps(r['code_fingerprints'],sort_keys=True))
  L=str(len(r['temporal_rad']));h=r['lens'][L]['entropy_nats'];assert len(h)==r['total_tokens']
  p=r['first_turn_positions'];assert all(r['prompt_tokens']<=i<r['total_tokens'] for i in p)
  assert math.isfinite(r['H_next_direct']['H_next'])
  boundary=r['turn']['boundary'];prefix=r['turn']['full_text'][:r['turn']['end_char']]
  if boundary and prefix.count('<think>')>prefix.count('</think>'):audit['boundary_inside_think'].append([model,r['id'],boundary])
  window=r['spans'].get('conflict',[]);kind='conflict' if window else None
  if q['id'] in constraints:
   phrase=constraints[q['id']];start=r['prompt'].rfind(phrase);assert start>=0
   off=tok(r['prompt'],add_special_tokens=False,return_offsets_mapping=True)['offset_mapping']
   window=[i for i,(a,b) in enumerate(off) if b>start and a<start+len(phrase)];kind='constraint'
  wm=None if not window else {'kind':kind,'positions':window,'H':float(np.mean([h[i] for i in window])),'temporal_rad':float(np.mean([r['mid_temp_rad'][i] for i in window])),'layer_one_minus_cos':float(np.mean([r['mid_layer_one_minus_cos'][i] for i in window]))}
  row=dict(model=model,id=r['id'],condition=r['group'],question=q,grade=grades[bid],blind_id=bid,H_next=r['H_next_direct']['H_next'],window=wm,first=r['first_turn_metrics'],full=r['full_metrics'],first_repeat4=r['first_turn_repeat4'],full_repeat4=r['full_repeat4'],first_end=r['first_turn_end_observed'],hit_limit=r['hit_limit'],turn=r['turn'],input_ids=r['token_ids'][:r['prompt_tokens']],generated_ids=r['generated_token_ids'],prompt=r['prompt'],replay_agreement=r['cached_vs_replay_greedy_agreement'],peak_GiB=r['peak_cuda_allocated_GiB'],output_special_ids=r['output_special_ids'],code_fingerprints=r['code_fingerprints'])
  data.append(row)
 assert len(fingerprints)==1
 for c in conditions:
  rr=[r for r in data if r['model']==model and r['condition']==c['id']];assert len(rr)==14
  a=next(r for r in rr if r['question']['id']=='trap_fact_age');b=next(r for r in rr if r['question']['id']=='logic_age')
  audit['duplicate_age'].append(dict(model=model,condition=c['id'],same_input=a['input_ids']==b['input_ids'],same_output=a['generated_ids']==b['generated_ids'],H_next_delta=a['H_next']-b['H_next'],score_delta=a['grade']['score']-b['grade']['score']))
assert not audit['boundary_inside_think'],audit['boundary_inside_think']
base={r['id']:r for r in data if r['model']==models[0]};post={r['id']:r for r in data if r['model']==models[2]}
assert all(base[k]['input_ids']==post[k]['input_ids'] for k in base);audit['base_post_identical_input_ids']=126

def mean(v):
 v=[x for x in v if x is not None];return sum(v)/len(v) if v else None
def hard(r):return r['question']['target'] and not r['question']['ambiguous'] and r['question']['id']!='logic_age'
def frac(rr):return f"{sum(r['grade']['score'] for r in rr)}/{len(rr)}"
def fmt(v):return 'NA' if v is None else f'{v:.3f}'
summaries=[]
for m in models:
 for c in conditions:
  rr=[r for r in data if r['model']==m and r['condition']==c['id']];target=[r for r in rr if r['question']['target']];hh=[r for r in rr if hard(r)]
  s=dict(delivered_hard_score=sum(r['grade']['score'] for r in hh if r['turn']['first_text'].count('<think>')<=r['turn']['first_text'].count('</think>')),model=m,condition=c['id'],hard_score=sum(r['grade']['score'] for r in hh),hard_n=len(hh),hard_lenient=sum(r['grade'].get('lenient_score',r['grade']['score']) for r in hh),trap=frac([r for r in rr if r['question']['family']=='trap']),logic=frac([r for r in rr if r['question']['family']=='logic']),control=frac([r for r in rr if not r['question']['target']]),spatial=frac([r for r in rr if r['question']['id'] in ['trap_space_table','trap_space_wall']]),shirt=frac([r for r in rr if r['question']['ambiguous']]),H_next=mean([r['H_next'] for r in target]),H_gen=mean([r['first']['H_gen'] for r in target if r['first']]),H_conflict=mean([r['window']['H'] for r in rr if r['question']['family']=='trap']),temporal_rad=mean([r['first']['temporal_rad'] for r in target if r['first']]),layer_one_minus_cos=mean([r['first']['layer_one_minus_cos'] for r in target if r['first']]),first_repeat_count=sum(r['first_repeat4'] is not None and r['first_repeat4']>=.5 for r in target),first_repeat_eligible=sum(r['first_repeat4'] is not None for r in target),full_repeat_count=sum(r['full_repeat4'] is not None and r['full_repeat4']>=.5 for r in target),first_repeat_mean=mean([r['first_repeat4'] for r in target]),full_repeat_mean=mean([r['full_repeat4'] for r in target]),first_end=sum(r['first_end'] for r in target),first_tokens=mean([r['first']['n'] for r in target if r['first']]),grade_status=dict(collections.Counter(r['grade']['status'] for r in target)))
  summaries.append(s)
(R/'results.json').write_text(json.dumps(dict(protocol=protocol,audit=audit,summary=summaries,records=data),ensure_ascii=False,indent=2))
(R/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
lines=['# 原生关系标签对照实验：Mother/I 与 User/Assistant','', '2026-11-03，DGX Spark GB10；三模型 × 九种前缀 × 十四题，共 378 次生成。主实验是 Qwen3.5-35B-A3B-Base；另外完整运行同尺寸后训练版和 Qwen3-0.6B。','', '## 实验与判分','', '所有输入均为普通文本，实际输入 token ID 已核验不含特殊词元。Base 与后训练 35B 的 126 对输入 token ID 完全相同。三个日常示例固定为下雨带伞、书放书架、手机充电；只替换每轮问答两端标签。qa_0 是额外零示例对照。英文组仍用相同中文正文；中文组共用全角冒号，英文组共用冒号加空格。跨语言比较因此也包括字形和分词差异。','', '每题贪心生成最多 160 tokens，未在下一轮标签处强制停止。首轮在下一条提问者标签或模型输出的结束特殊词元前截取；若模型重复输出应答者标签，仍保留在首轮。完整续写另外保存。主分数按可见首轮核心结论人工判定，未给结论的截断分析计未答；已经明确给出正确判断但未写完的分析记命中，并单列完整性。相同题目和相同答复共用一份判分。','', '6 道陷阱与 5 道逻辑题里的年龄题完全相同，因此主汇总去重；衣物题的动作可行性依赖开口、松紧等未充分限定条件，另报“按任务预期拒绝”的命中，主分数排除它。主分数共 9 道：桌子、密封玻璃、三道事实题、蜡烛、星期、鸡兔、球价。年龄题必须指出前提不可能，单答负五岁不算拆穿；战机题单答零不算明确识别错误前提，另给宽松口径。三个正常控制题检验是否只是一律反对。','', '## 正确率与对照','', '|模型|标签|主分数/9|宽松/9|空间/2|陷阱/6*|逻辑/5*|衣物预期/1|正常控制/3|','|---|---|---:|---:|---:|---:|---:|---:|---:|']
for s in summaries:lines.append(f"|{s['model']}|{s['condition']}|{s['hard_score']}/9|{s['hard_lenient']}/9|{s['spatial']}|{s['trap']}|{s['logic']}|{s['shirt']}|{s['control']}|")
lines+=['','*陷阱与逻辑两栏保留原题单口径，年龄出现两次；不可把两栏相加当独立题数。衣物栏是任务预期判断，不是普适物理定理。','', '## 配对比较','']
lines[-2:-2]=['更严口径仅计已经退出显式 think 分析的正确答复（不是保证完整结束标记），避免把分析中的正确知识视为已交付最终答案。','', '|模型|标签|退出分析后正确/9|','|---|---|---:|']+[f"|{s['model']}|{s['condition']}|{s['delivered_hard_score']}/9|" for s in summaries]+['']
for m in models:
 for a,b in [('mother_zh','service_zh'),('mother_en','service_en'),('partner','service_zh'),('friend','service_zh'),('boss','service_zh'),('qa_3','qa_0')]:
  aa={r['question']['id']:r for r in data if r['model']==m and r['condition']==a and hard(r)};bb={r['question']['id']:r for r in data if r['model']==m and r['condition']==b and hard(r)}
  dif=[aa[k]['grade']['score']-bb[k]['grade']['score'] for k in aa]
  lines.append(f"- {m}，{a} 对 {b}：赢 {dif.count(1)}、输 {dif.count(-1)}、平 {dif.count(0)}（同一 9 题）。")
lines+=['','## 熵、曲率与复读','', '![各条件正确率、熵、曲率与复读](relation_tags/comparison.svg)','', 'H_next 来自实际生成首步 LM head 的完整词表分布；H_gen 为首轮所生成 token 的前一位置预测熵，单位 nats。H_conflict 为六道陷阱中预定义触发词 token 位置预测下一个 token 的熵。逻辑题另存明确约束词窗口（蜡烛耗尽、35岁、早两天、28条腿、贵100元），称约束窗口，不冒称所有题都有语义冲突。','', '曲率复用既有协议：时间曲率是连续三个 token 残差增量的转角（弧度）；跨层曲率是相邻层残差增量方向的 1−cos。均在模型深度 50%–85% 的层区间平均，再在首轮 token 内平均。这些量来自对已生成序列的一次无缓存重放；不是直接记录生成时每个缓存状态。H_next 为生成实测，其余熵/几何来自重放。','', '|模型|标签|H_next|H_gen首轮|H_conflict|时间角|跨层1−cos|首轮token均值|首轮重复≥.5/可测|全文重复≥.5/11|观察到首轮结束/11|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for s in summaries:lines.append('|'+ '|'.join([s['model'],s['condition']]+[fmt(s[k]) for k in ['H_next','H_gen','H_conflict','temporal_rad','layer_one_minus_cos','first_tokens']]+[f"{s['first_repeat_count']}/{s['first_repeat_eligible']}",f"{s['full_repeat_count']}/11",f"{s['first_end']}/11"] )+'|')
lines+=['','熵及曲率表在原 11 道目标题上等权平均（年龄重复保留，以便与原题单逐项核对）；主正确率另按独立 9 题。短于四 token 的回答无法形成 4-gram，记 NA，不当作零复读。重复指标为 1−不同 token 四元组数/四元组总数；≥0.5 是描述性阈值，不能证明无限死循环。全文高复读可能是首轮结束后模型反复自问自答，必须与首轮指标分开。','', '## 验证与限制','']
audit['replay_agreement_min']=min(r['replay_agreement'] for r in data);audit['replay_agreement_mean']=mean([r['replay_agreement'] for r in data]);audit['peak_allocated_GiB']=max(r['peak_GiB'] for r in data)
lines += [f"- 全部 378 条输入无特殊词元；各模型测量代码指纹一致；Base/Post 126 对输入 ID 相同。首轮边界落在未闭合 think 内：{len(audit['boundary_inside_think'])}。",f"- 缓存生成与无缓存重放逐 token 贪心一致率：最低 {audit['replay_agreement_min']:.4f}，记录均值 {audit['replay_agreement_mean']:.4f}。数值/实现路径差异存在，尤其低间隔 logits，不能把重放几何视为生成时完全相同的内部轨迹。", f"- 峰值 CUDA 已分配 {audit['peak_allocated_GiB']:.2f} GiB；单模型串行驻留，35B 使用原生 BF16 分片加载，所有 GPU 运算均在 Spark。",f"- 年龄重复输入输出一致 {sum(x['same_output'] for x in audit['duplicate_age'])}/{len(audit['duplicate_age'])} 对；原始核查在 audit.json。",'- 单个固定题集、单次贪心样本，未测随机种子分布或吸引域体积；正确率只代表这些题目，不能直接称为全局智商。标签同时更改提问者与应答者，不能孤立归因于“我”一个词；也未构造真实的长期母子/伴侣关系。','- 熵高低、转角大小本身都不是聪明或自我的判据；判断先看实际答复与正常题控制。不预设某段熵是黄金区间。','','## 原话与复现文件','','完整 378 条首轮与至多 160-token 原续写见 [transcripts.md](relation_tags/transcripts.md)。[results.json](relation_tags/results.json) 包含全部输入、token ID、判分、熵、曲率汇总及边界；逐层逐 token 原始数组保存在 Spark raw/，随附 raw.tar.gz。协议、脚本、人工判分缓存和运行日志均在 relation_tags/。','']
intro=['## 这次测到了什么','',
'主实验没有支持 Mother/I 比 User/Assistant 更强的普遍结论。Base：中文妈妈/我 5/9，对用户/助手 7/9；英文 Mother/I 5/9，对 User/Assistant 6/9。爱人/我 5/9，朋友/我 6/9，老板/员工 5/9，问/答三示例与零示例均 4/9。这里的分数按预先写明的可见核心结论口径，退出显式分析后的口径另表。',
'', '同尺寸后训练模型：中文两组均 4/9；英文两组均 7/9。英文 Mother/I 正常控制 3/3，User/Assistant 1/3，因此在这几个正常题上有局部差异；不能仅凭主分数相等就说行为完全相同。0.6B 的中文两组均 1/9，英文 Mother/I 0/9、User/Assistant 1/9。',
'', '熵随前缀改变，但没有按理论预期统一收敛到更低、更准的状态。Base 中文妈妈/我 H_next=3.692、H_gen=1.703 nats，用户/助手为 3.357、1.420；英文 Mother/I 为 3.100、1.502，User/Assistant 为 2.933、1.227。母子标签在这两对上都提高了平均熵，同时主分数更低。单纯标签足以改变分布，尚不足以证明更强吸引域或更高智商。',
'', 'Base 九组的首轮重复阈值事件全部为零；多数首轮只是很短的直接答案。完整续写则高度重复，妈妈/我 10/11、用户/助手 9/11 达到重复阈值。母子标签没有治好后续问答循环。这里观察的是最多160词元的有限行为，不能称为无限循环率。',
'', '一条清晰反例：Base 妈妈/我回答诸葛亮“击落了曹操的10艘战船”，并在后续几轮反复重复同一错误；用户/助手明确说“并没有驾驶歼-20战机击落曹操的战船”，也随后反复重复这一正确答复。Base 妈妈/我对十米桌首答“合理”，随后转而自问“昨天去了火星”意味着什么；那些后续新题的正确回答没有被拿来补本题得分。',
'', '本次检验的是几个前缀词能否立即产生效果；没有加入共同经历、关系叙事或长期互动。因此这些阴性及混合结果直接约束的是“仅换角色标签就提升”的版本，不覆盖更丰富的关系上下文设想。','']
lines=lines[:4]+intro+lines[4:]
(R.parent/'relation_tags_report.md').write_text('\n'.join(lines))
trans=['# 全部原话：首轮与完整续写','']
for r in data:
 trans += [f"## {r['model']} / {r['condition']} / {r['question']['id']}",'',r['question']['text'],'',f"首轮判分 {r['grade']['score']}；{r['grade']['status']}；首轮结束被观察到={r['first_end']}；4gram首轮={r['first_repeat4']}，全文={r['full_repeat4']}",'','首轮：','```text',r['turn']['first_text'],'```','','完整生成（含模型输出控制词）：','```text',r['turn']['full_text'],'```','']
(R/'transcripts.md').write_text('\n'.join(trans));(R/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
(R/'results.json').write_text(json.dumps(dict(protocol=protocol,audit=audit,summary=summaries,records=data),ensure_ascii=False,indent=2))
print(json.dumps(summaries,ensure_ascii=False,indent=2))
