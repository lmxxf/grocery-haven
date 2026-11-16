"""Rebuild reports and insert the completed experiment's interpretation from cached outputs."""
import json,sys,hashlib,math
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent;H=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3/experiments/exp1b_archaic_nucai');sys.path.insert(0,str(R))
import report_exp1b as report
read=lambda p:json.loads(Path(p).read_text())
rs=read(H/'all_layers_full.json');rd=read(R/'representative_readouts.json');reps=read(R/'representatives.json');geometry=read(R/'axis_geometry.json');probes=read(R/'probes.json');pairs=read(R/'pairs.json');samples=read(R/'samples.json')
report.build(rs,rd,reps,geometry,probes,pairs,samples)
v0=rs[16]['references']['Moral_Nonliteral']['delta'];v1=rs[30]['references']['Moral_Nonliteral']['delta'];w='W2_shared'
r1=lambda l:rs[l]['references']['R1_Humiliation']['delta'];r2=lambda l:rs[l]['references']['R2_Court']['delta']
pair=lambda v,group,alt:v['cohorts'][w][group]['minimal_pairs'][alt]
fmt=report.f
cal=report.selection(rs)['calibration'];rel=100*(1-cal['W2']['median_abs_residual']/cal['W0']['median_abs_residual'])
def ci(x):return '['+', '.join(fmt(v)for v in x['ci95'])+']'
core='''<!-- findings-start -->
## 核心判读

**朝仪／公文与一般贬损评价可以分开；本轮没有获得一根可直接命名为“纯人格羞辱”的专属轴，也没有测到“把臣换成奴才必然增加羞辱”的全层规律。**

'''
core+=f"1. **长古文最好，但不是全层洗净。** 38个通过同义词留出及独立卑鄙检验的L10–L48轴上，现代参照归一化残留的绝对值中位数：W0={cal['W0']['median_abs_residual']:.3%}，W1={cal['W1']['median_abs_residual']:.3%}，W2={cal['W2']['median_abs_residual']:.3%}，W3a={cal['W3a']['median_abs_residual']:.3%}，W3b={cal['W3b']['median_abs_residual']:.3%}。W2相对W0中位数降低{rel:.2f}%；不能把‘相对于现代锚剩17%’说成‘短句原先100%污染被清掉83%’。\n"
core+=f"2. **浅中层与中层差异很大。** L16 C{v0['axis']}（κ={fmt(v0['kurtosis'])}，同义词留出4/4、卑鄙8/8）的W0/W2残留为{v0['calibration']['W0']['normalized_modern_gap']:.2%}/{v0['calibration']['W2']['normalized_modern_gap']:.2%}，相对W0只消除{v0['calibration']['W2']['removal_percent_vs_W0']:.2f}%。L30 C{v1['axis']}（κ={fmt(v1['kurtosis'])}，同样4/4与8/8）的对应残留为{v1['calibration']['W0']['normalized_modern_gap']:.2%}/{v1['calibration']['W2']['normalized_modern_gap']:.2%}，这根轴原本就接近中性基线，W2进一步接近。英文前缀没有总体胜过真实长古文。\n"
core+='3. **浅中层两路响应有清楚分工。** 在W2_shared下，L18外源R1候选C1376的A1/A2/B/C原始均值为'+ '/'.join(fmt(r1(18)['cohorts'][w][g]['raw']['mean'])for g in ['A1','A2','B','C'])+'；同层外源R2候选C1816为'+ '/'.join(fmt(r2(18)['cohorts'][w][g]['raw']['mean'])for g in ['A1','A2','B','C'])+'。两轴reading cosine=-0.00635、writing cosine=0.01576，接近直角。J词表给前者weird/absurd/crap/nonsense，后者request/信函/pleading/请示：更准确的名称是一般贬损／口语评价与请求文书通道，不是两个已经证实的独立心理感受。\n'
core+='4. **中深层也能分出公文与错误评价。** L45 C1194（κ=43.7778）J正极为一律、各部、各省、按规定、手续、事宜；L45外源R1选出的C1564（κ=26.7841）则为错误的、错误、incorrect、erroneous、mistakes。两轴reading cosine=-0.00178、writing cosine=0.01957；确实不同，但后一根是错误／负面评价轴，不能仅因它由屈辱词选出就改名为纯羞辱轴。\n'
for l in [18,31,45]:
 v=r1(l);a=pair(v,'A1','臣');b=pair(v,'A2','我');core+=f"5{chr(97+[18,31,45].index(l))}. **L{l} C{v['axis']}最小配对**：A1奴才−臣={fmt(a['mean'])}，95%CI {ci(a)}，为现代外源差的{a['normalized_mean']:.2%}；A2奴才−我={fmt(b['mean'])}，CI {ci(b)}。A1词均值口径={fmt(a['mean_token']['mean'])}；A2词均值口径={fmt(b['mean_token']['mean'])}。\n"
core+='   这些差并不全为正：L18两个主差均为负，L31有小正差，L45末token区间跨0。不能从其中一层的正值推成不可避免的卑贱位移，也不能因原始z接近0就判定“感受完全没有”。\n'
a=pair(r2(45),'A1','臣');core+=f"6. **身份公文位移有单独信号。** L45公文C1194的A1奴才−臣={fmt(a['mean'])}，CI {ci(a)}；词均值={fmt(a['mean_token']['mean'])}，CI {ci(a['mean_token'])}。但L41朝仪C3492上该差为{fmt(pair(r2(41),'A1','臣')['mean'])}，说明‘奴才比臣更朝仪’也不能作为不分层的单方向定律。\n"
core+='7. **内源最强分组轴里有语法人称混杂。** L48的B−A2 Top1为C335，原J正极myself/my/我自己/ourselves。它以相反方向切分挨骂与自称，文档留出9/9，但主要提示“是否第一人称自指”，不是羞辱专轴。L45 A1−C Top1 C1194文档留出5/5，对应公文措辞，含义更明确。只看分类准确率会把这两种机制混在一起。\n'
core+='8. **近零判断对口径敏感。** 例如L31的A2奴才−我，末token差约0.634落在预定±10%现代差等价带内；词内均值差约1.344更大。A2相对下官的差在部分代表轴还会随末token／词均值口径换号。因此本轮不写“奴才自称已经彻底洗净羞辱”这样的总判。\n\n'
core+='### 杨宗仁原折的专门核对\n\n原折故宫022688的奴才位于奏首，只有“湖广总督”在其左侧。以下是该单例同前缀奴才−臣；它与十份奏折平均分开报告。\n\n|L/轴|short|W2_native（同原短左文）|W2_shared|W3|\n|---|---|---|---|---|\n'
z=np.load(H/'z_last.npy',mmap_mode='r')
for l,name in [(18,'R1_Humiliation'),(18,'R2_Court'),(45,'R1_Humiliation'),(45,'R2_Court')]:
 v=rs[l]['references'][name]['delta'];c=v['axis'];values=[]
 for ww in ['short','W2_native','W2_shared','W3']:
  ix={s['target']:s['id']for s in samples if s['sample_id']=='Yang_022688'and s['wrapper']==ww};values.append(float((z[l,ix['奴才'],c]-z[l,ix['臣'],c])*v['sign']))
 core+=f'|L{l} C{c} {name}|'+ '|'.join(fmt(x)for x in values)+'|\n'
core+='\n此例在浅层的方向也会随包裹改变，不拿奏折群体均值替代杨宗仁本人这一条。\n<!-- findings-end -->\n'
p=R/'report_exp1b.md';first,rest=p.read_text().split('\n',1);p.write_text(first+'\n\n'+core+'\n'+rest.lstrip('\n'))
readme=R/'README.md';old=readme.read_text();first,rest=old.split('\n',1);brief='''

主要发现：

- 38个有效层上，W2相对现代道德锚的残留中位数17.0%，W0为21.0%；长古文优于英文，但没有全层归零。
- 公文／朝仪与一般负面评价能分开；J词表未支持把负面评价专称为“人格羞辱”。
- 奴才−臣的负面轴位移随层可正可负，词均值也会影响幅度；不支持不可避免的正向羞辱位移。
- 内源高准确率轴C335主要显影第一人称，而非羞辱；原文、替换对照与这些混杂都已保留。
''';readme.write_text(first+brief+'\n'+rest.lstrip('\n'))
# Persist corrected probe hash after navigation removal; avoid stale design provenance.
design=read(R/'design.json');design.setdefault('sha256_before_navigation_cleanup',design['sha256']);design['sha256']=hashlib.sha256((R/'probes.json').read_bytes()).hexdigest();design['source_navigation_removed']=True;(R/'design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2))
# Keep tokenization output in the requested main run log, after the successful run is closed.
log=R/'run.log';data=log.read_text()
if not data.startswith('TOKENIZATION_PRE_FORWARD'):
 log.write_text('TOKENIZATION_PRE_FORWARD (recorded by prepare_exp1b.py before model load)\n'+(R/'prepare.log').read_text()+'\n'+data)
# Validate delivery layout and recorded calculations without any new model call.
assert len(rs)==64 and len(rd)==len(reps)==10
assert all(len(x['positive_top25'])==25 and len(x['negative_top25'])==25 for x in rd)
assert all('上一回\n回目录\n下一回\n' not in p['text'] and p['text'].endswith(p['target'])for p in probes)
assert not [p for p in R.rglob('*')if p.is_file()and p.stat().st_size>10_000_000]
assert all(Path(H/name).exists()for name in ['activations_last.npy','activations_mean.npy','z_last.npy','z_mean.npy','all_layers_full.json'])
validation=read(R/'validation.json');assert validation['all_scores_finite'] and validation['causal_target_last']
print('FINAL_DELIVERY_PASS',len(probes),'probes',len(rs),'layers',len(reps),'readouts')
print('REPORT',str(R/'report_exp1b.md'))
print('W2_RESIDUAL_MEDIAN',cal['W2']['median_abs_residual'])
