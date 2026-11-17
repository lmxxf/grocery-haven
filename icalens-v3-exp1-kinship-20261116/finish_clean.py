"""Validate the blood-symmetric rerun and write only measured findings."""
from pathlib import Path
import json,time,hashlib
import numpy as np
import run_exp1a as e
OUT=e.OUT;H=e.HEAVY;OLD=H/'history_before_blood_symmetric_20261117';LAYERS=[13,25,26,37,42]
def fingerprint(probes,pairs,groups,name):
 rows=[]
 for i in groups[name]:
  p=pairs[i];a=probes[p['a']];b=probes[p['b']];rows.append(dict(a=a['text'],b=b['text'],target_a=a['target'],target_b=b['target'],input_a=a['input_ids'],input_b=b['input_ids'],metadata={k:v for k,v in p.items()if k not in ['a','b']}))
 return hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def label(v,g):x=v['groups'][g];return f"{x['correct']}/{x['n']}"
def run(results,readouts,probes,pairs,groups,meta):
 oldp=e.load(OLD/'probes.json');oldpairs=e.load(OLD/'pairs.json');oldgroups=e.load(OLD/'groups.json');oldresults=e.load(OLD/'results_all_layers.json')
 checks={}
 for g in ['H1','no_outer','cousins','outer','EN_A','EN_B','EN_C','physical','social']:
  a=fingerprint(oldp,oldpairs,oldgroups,g);b=fingerprint(probes,pairs,groups,g);checks[g]=dict(before=a,after=b,identical=a==b,n_pairs=len(groups[g]));assert a==b,g
 assert e.S2==[('伯父','大舅'),('叔叔','舅舅'),('姑姑','姨妈')]
 assert e.S1==e.S2+[('堂哥','表哥'),('堂姐','表姐'),('堂弟','表弟')]
 assert all('姨夫'not in p['text'] and p['target']!='叔父' for p in probes)
 e.save('holdout_unchanged.json',checks)
 z=np.load(H/'z_last.npy',mmap_mode='r');zm=np.load(H/'z_mean.npy',mmap_mode='r');before_z=np.load(OLD/'z_last.npy',mmap_mode='r');oldlookup={(p['text'],p['target']):p['id']for p in oldp};matching=[(p['id'],oldlookup[p['text'],p['target']])for p in probes if(p['text'],p['target'])in oldlookup]
 forward_diffs=[float(np.max(np.abs(z[l,[a for a,b in matching]]-before_z[l,[b for a,b in matching]])))for l in range(64)]
 core=[];legacy=[]
 oldaxes={13:2665,25:3140,26:3526,37:2923,42:1992}
 for l in LAYERS:
  for selector in ['S1','S2']:
   st=e.vector_stats(z[l],pairs,groups[selector]);c=oldaxes[l];sign=float(np.sign(st['mu'][c])or 1)
   legacy.append(dict(layer=l,selector=selector,old_axis=c,rank_by_delta=int((np.abs(st['mu'])>abs(st['mu'][c])).sum()+1),rank_by_t=int((np.abs(st['t'])>abs(st['t'][c])).sum()+1),new_selection_delta=float(st['mu'][c]),old_selection_axis=oldresults[l]['selectors'][selector]['delta'][0]['axis'],old_selection_delta=oldresults[l]['selectors'][selector]['delta'][0]['fit']['delta'],unchanged_holdout_at_old_axis={g:e.measure(e.vector_stats(z[l],pairs,groups[g]),c,sign,pairs,groups[g])for g in ['H1','no_outer','cousins','outer','EN_A','EN_B','EN_C']}))
   for method in ['delta','t']:
    v=results[l]['selectors'][selector][method][0];core.append(dict(layer=l,selector=selector,method=method,axis=v['axis'],sign=v['sign'],kurtosis=v['kurtosis'],fit_delta=v['fit']['delta'],fit_d=v['fit']['d'],groups={g:{k:v['groups'][g][k]for k in ['correct','n','oriented_delta','d']}for g in ['H1','no_outer','cousins','outer','EN_A','EN_B','EN_C','physical','social']},mean_token_groups={g:{k:v['mean_token_groups'][g][k]for k in ['correct','n','oriented_delta','d']}for g in ['H1','no_outer','cousins','outer','EN_A','EN_C']},independent_top1=results[l]['independent_top1']))
 e.save('core_rerun_numbers.json',core);e.save('legacy_axis_audit.json',legacy)
 # Independent public API verification on newly extracted residuals.
 from icalens import ICALens
 lens=ICALens.from_pretrained(e.ASSET);h=np.load(H/'activations_last.npy',mmap_mode='r');public=[]
 for l in [0,13,32,63]:
  actual=lens.transform(np.array(h[l,:2]),layer=l);error=float(np.abs(actual-z[l,:2]).max());assert error<1e-3;public.append(dict(layer=l,max_abs_error=error))
 e.save('projection_public_api_check.json',public)
 index=[]
 for r in results:
  index.append(dict(layer=r['layer'],selectors={s:{m:{k:r['selectors'][s][m][0][k]for k in ['axis','sign','kurtosis']}for m in ['delta','t']}for s in ['S1','S2']}))
 e.save('all_layers_index.json',index)
 import enrich_exp1a
 enrich_exp1a.run()
 table=['|层|S2均值差Top1|κ|选轴Δz|无外字|堂表|含外字|H1|EN-A|EN-C|','|---|---|---|---|---|---|---|---|---|']
 for l in LAYERS:
  v=results[l]['selectors']['S2']['delta'][0];table.append(f"|L{l:02d}|C{v['axis']}|{v['kurtosis']:.3f}|{v['fit']['delta']:.4f}|{label(v,'no_outer')}|{label(v,'cousins')}|{label(v,'outer')}|{label(v,'H1')}|{label(v,'EN_A')}|{label(v,'EN_C')}|")
 detail=['|层|选轴口径|C(均值差/t)|H1(均值差/t)|EN-A(均值差/t)|EN-C(均值差/t)|','|---|---|---|---|---|---|']
 for l in LAYERS:
  for s in ['S1','S2']:
   a=results[l]['selectors'][s]['delta'][0];b=results[l]['selectors'][s]['t'][0];detail.append(f"|L{l:02d}|{s}|{a['axis']}/{b['axis']}|{label(a,'H1')}/{label(b,'H1')}|{label(a,'EN_A')}/{label(b,'EN_A')}|{label(a,'EN_C')}/{label(b,'EN_C')}|")
 legacy_table=['|层|旧S2主轴|新S2均值差排名|新S2 t排名|新选轴集上的原轴Δz|','|---|---|---|---|---|']
 for x in legacy:
  if x['selector']=='S2':legacy_table.append(f"|L{x['layer']:02d}|C{x['old_axis']}|{x['rank_by_delta']}|{x['rank_by_t']}|{x['new_selection_delta']:.4f}|")
 intro='## 2026-11-17 血缘对称重跑\n\nS2 = 伯父/大舅、叔叔/舅舅、姑姑/姨妈；S1再加堂哥/表哥、堂姐/表姐、堂弟/表弟。旧版含姨夫的选轴结论已被本次替换，不沿用旧摘要。\n\n'+'\n'.join(table)+'\n\n'+'\n'.join(detail)+'\n\n旧轴是否仍是Top1：\n\n'+'\n'.join(legacy_table)+'\n\n'
 for rd in readouts:
  intro+=f"L{rd['layer']:02d} C{rd['axis']} J正极前10："+', '.join(json.dumps(t['text'],ensure_ascii=False)for t in rd['positive_top25'][:10])+'。\n\n'
 report=OUT/'report_exp1a.md';body=report.read_text();first,rest=body.split('\n',1);report.write_text(first+'\n\n'+intro+rest.lstrip('\n')+f'\n重数据统一存放 `{H}`；完整64层统计为该目录下results_all_layers.json。轻量代码和结果以当前归档目录为准。\n')
 readme=['# Exp1A：血缘对称版重跑（2026-11-17）','', '本版修正原选轴集中姨夫的姻亲污染。原版本可从git历史及重数据history目录追回。','', '- S2：伯父/大舅、叔叔/舅舅、姑姑/姨妈。','- S1：S2加堂哥/表哥、堂姐/表姐、堂弟/表弟。',f'- {len(probes)}条唯一裸文本、全64层重新前向；模型一次加载。末token与目标词均值两口径都跑。','- H1、no_outer、cousins、outer、EN-A/B/C、physical、social的原文、token IDs及配对元数据哈希全部与旧版相同。','', '主表为干净S2均值差选轴，完整S1/S2×均值差/t结果见[报告](report_exp1a.md)和core_rerun_numbers.json。','']+table+['']+detail+['','旧轴新排名：','']+legacy_table+['','各组效应量、原始差值、均值token稳健性：core_rerun_numbers.json；固定五层J-Lens完整Top25与语料：representative_readouts.json。','',f'重数据：`{H}`（activations_*.npy、z_*.npy、results_all_layers.json、top3_joint_statistics.json）。旧污染版：history_before_blood_symmetric_20261117/。','', '复现：`bash run_all.sh`。代码和轻量产物直接写本目录，不再从重数据目录运行旧脚本。','', '验收：holdout_unchanged.json、projection_public_api_check.json、validation.json。']
 (OUT/'README.md').write_text('\n'.join(readme)+'\n')
 # Remove stale statements about matching v1 token counts/old representatives from generic report footer.
 text=report.read_text().replace('EN-C 同时给出父母姓名','EN-C 按五套姓氏聚类；同时给出父母姓名');report.write_text(text)
 from collections import Counter
 valid=dict(all_64_layers=len(results)==64,all_scores_finite=bool(np.isfinite(z).all()and np.isfinite(zm).all()),blood_symmetric_S1=e.S1,blood_symmetric_S2=e.S2,all_holdout_groups_identical=all(x['identical']for x in checks.values()),EN_C_same_token_bags=all(Counter(probes[p['a']]['input_ids'])==Counter(probes[p['b']]['input_ids'])for p in pairs if p['group']=='EN_C'),matching_old_probe_count=len(matching),unchanged_probe_z_max_abs_by_layer=forward_diffs,public_transform_checks=public)
 assert valid['all_scores_finite']and valid['EN_C_same_token_bags'];e.save('validation.json',valid)
 with(OUT/'DevHistory.md').open('a')as f:f.write('\n## '+time.strftime('%Y-%m-%d %H:%M:%S %z')+'｜Step 2 全64层收官与旧轴复核\n\n'+f"新前向{len(probes)}条，模型加载{meta['model_loads']}次。九个留出/对照组哈希逐个一致；与旧版相同的{len(matching)}条探针重新前向后，ICA坐标最大差为{max(forward_diffs):.8g}。公开ICALens.transform独立核验最大误差{max(x['max_abs_error']for x in public):.8g}。\n\n"+'\n'.join(table)+'\n\n'+ '\n'.join(detail)+'\n\n'+ '\n'.join(legacy_table)+'\n\n以上只记重跑读数；旧版关于L13三冠王、中层婚姻算子及英文传染的文字不得直接照搬。请按新Top1和固定旧轴排名分别判断。\n')
 for name in ['README.md','report_exp1a.md']:
  p=OUT/name;p.write_text(p.read_text()+'\n## 与原摘要直接相关的变化\n\n- L13：S1均值差仍选C2665，但t改选C383；干净S2均值差/t分别选C1540/C3599。旧“双准则同轴三冠王”不再成立；C2665在新S2均值差中排第2。\n- L25/L26：去掉姨夫后，均值差主轴仍为C3140/C3526，三组中文留出各10/10、20/20、30/30。\n- L37：旧C2923在干净S2均值差中降到第11；新Top1 C1374的EN-A为15/25，旧25/25不能继续当作新选轴结果。\n- L42：旧C1992在干净S2均值差中排第3；新C3872（κ=2.322）EN-C仍15/15，J读出主词是引号/标点，不能将它沿用为旧版“嫁给/marriage”词牌。\n- 255条同文探针重新前向的ICA坐标与旧版最大差为0；变化来自选轴集替换，而非修改留出、换模型或读取错缓存。\n')
 print('\n'.join(table),flush=True);print('CLEAN_RERUN_COMPLETE',meta,flush=True)
if __name__=='__main__':
 run(e.load(H/'results_all_layers.json'),e.load(OUT/'representative_readouts.json'),e.load(OUT/'probes.json'),e.load(OUT/'pairs.json'),e.load(OUT/'groups.json'),e.load(OUT/'run_metadata.json'))
