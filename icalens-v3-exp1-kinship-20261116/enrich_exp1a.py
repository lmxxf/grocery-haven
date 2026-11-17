"""No model reload: audit completed outputs and quantify Top2/3 joint responses."""
from pathlib import Path
import json,sys,itertools
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));import run_exp1a as e
HEAVY=e.HEAVY

def run():
 results=e.load(HEAVY/'results_all_layers.json');pairs=e.load(ROOT/'pairs.json');groups=e.load(ROOT/'groups.json');probes=e.load(ROOT/'probes.json')
 z=np.load(HEAVY/'z_last.npy',mmap_mode='r');zm=np.load(HEAVY/'z_mean.npy',mmap_mode='r')
 from collections import Counter
 checks={'all_scores_finite':bool(np.isfinite(z).all() and np.isfinite(zm).all()),'all_64_layers':len(results)==64,'EN_C_same_token_bag':all(Counter(probes[p['a']]['input_ids'])==Counter(probes[p['b']]['input_ids']) for p in pairs if p['group']=='EN_C'),'EN_A_C_same_target_ids':all(probes[p['a']]['target_ids']==probes[p['b']]['target_ids'] for p in pairs if p['group'] in ['EN_A','EN_C'])}
 # Independently compare paired-t calculations against scipy on one stored axis.
 from scipy.stats import ttest_rel
 r=results[32]['selectors']['S1']['t'][0];ii=groups['S1'];a=[pairs[i]['a'] for i in ii];b=[pairs[i]['b'] for i in ii];c=r['axis']
 actual=ttest_rel(z[32,a,c].astype('float64'),z[32,b,c].astype('float64')).statistic
 checks['scipy_paired_t_abs_error']=float(abs(actual*r['sign']-r['fit']['t']))
 assert all(checks[k] for k in ['all_scores_finite','all_64_layers','EN_C_same_token_bag','EN_A_C_same_target_ids']);assert checks['scipy_paired_t_abs_error']<1e-8
 entries=[]
 for layer in range(64):
  for sel in ['S1','S2']:
   fit=e.vector_stats(z[layer],pairs,groups[sel])
   for method in ['delta','t']:
    top=results[layer]['selectors'][sel][method];axes=[v['axis'] for v in top];sign=np.array([v['sign'] for v in top]);scale=fit['diff'][:,axes].std(0,ddof=1);scale=np.maximum(scale,1e-12)
    row={'layer':layer,'selector':sel,'method':method,'axes':axes,'top_axes_evidence':[], 'joint':{}}
    held=['H1'] if sel=='S1' else ['no_outer','cousins','outer']
    for v in top:
     row['top_axes_evidence'].append(dict(axis=v['axis'],fit_q_BH_5120=v['fit_q_BH_5120'],fit_cluster_p=v['fit']['cluster_exact_signflip_p'],heldout_cluster_p={g:v['groups'][g]['cluster_exact_signflip_p'] for g in held}))
    for k in [1,2,3]:
     all_joint=(np.asarray(z[layer])[:,axes[:k]]*sign[:k]/scale[:k]).mean(1)[:,None]
     row['joint'][str(k)]={g:e.measure(e.vector_stats(all_joint,pairs,groups[g]),0,1,pairs,groups[g]) for g in held+['EN_A','EN_C']}
    entries.append(row)
 e.save('top3_joint_statistics.json',entries);e.save('validation.json',checks)
 lines=['<!-- joint-analysis -->','## Top2/Top3 是否提供额外信息','', '联合读数使用训练集预先固定的符号与配对差标准差缩放：`joint_k = mean_i(sign_i * z_i / sd_fit(diff_i))`。不使用留出集拟合权重。比较1/2/3根轴的逐对符号准确率，检验是否比单根更好；轴间相关性和重复句框没有被当成额外独立样本。', '', '|L|口径/准则|Top3 C|中文单轴→双轴→三轴|EN-A单→双→三|EN-C单→双→三|Top2/3训练BH q|Top2/3训练词对置换p|','|---|---|---|---|---|---|---|---|']
 for row in entries:
  held=['H1'] if row['selector']=='S1' else ['no_outer','cousins','outer']
  seq=lambda g:'→'.join(e.acc(row['joint'][str(k)][g]) for k in [1,2,3])
  lines.append('|'+str(row['layer'])+'|'+row['selector']+'/'+row['method']+'|'+','.join(map(str,row['axes']))+'|'+ '; '.join(g+':'+seq(g) for g in held)+'|'+seq('EN_A')+'|'+seq('EN_C')+'|'+','.join(e.fmt(v['fit_q_BH_5120']) for v in row['top_axes_evidence'][1:])+'|'+','.join(str(v['fit_cluster_p']) for v in row['top_axes_evidence'][1:])+'|')
 lines+=['','## 输出核验','',json.dumps(checks,ensure_ascii=False),'','本次为2026-11-17血缘对称重跑。全部探针及固定五层读出在一次完整模型加载中完成；旧污染选轴数据已保留于重数据history目录。']
 p=ROOT/'report_exp1a.md';text=p.read_text().split('<!-- joint-analysis -->')[0];p.write_text(text+'\n'+'\n'.join(lines)+'\n')
 print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':run()
