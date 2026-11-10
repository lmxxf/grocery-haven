"""CPU-only validation and lossless transcript export for the requested grid."""
import json,time,math,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'experiment4_high_dose.json';x=json.loads(p.read_text())
assert x.get('complete') and len(x['runs'])==40
expected={('L38_prompt_last',a,c)for a in [2.,4.,8.,16.]for c in ['bread','hotpot','elephant','random']}|{(s,a,c)for s in ['L34_44_prompt_last','L34_44_prompt_and_decode']for a in [.2,.5,1.,2.]for c in ['bread','hotpot','random']}
assert {(r['scope'],r['alpha'],r['concept'])for r in x['runs']}==expected
maxnormerror=0.;decode_calls=0
for r in x['runs']:
 assert 'error'not in r
 g=r['generation'];assert g['tokens']==len(g['token_ids'])
 for l,tr in r['hook_trace'].items():
  assert len(tr)==(g['tokens']if r['include_decode_steps']else 1)
  assert tr[0]['sequence_width']==len(x['prompt_token_ids'])
  for j,t in enumerate(tr):
   assert t['forward_call']==j
   if j>0:assert t['sequence_width']==1;decode_calls+=1
   want=r['alpha']*x['clean_reference_norms'][l]
   assert abs(want-t['intended_delta_norm'])<1e-8
   assert all(math.isfinite(t[k])for k in ['norm_before','actual_delta_norm','actual_relative_to_current'])
   maxnormerror=max(maxnormerror,abs(t['actual_delta_norm']/want-1))
rows=[];groups={}
for r in x['runs']:
 a=r['analysis'];k=r['scope'];groups.setdefault(k,{'runs':0,'target_mentions':0,'self_report_lexical_candidates':0,'quantum_present':0,'repeat_stops':0})
 groups[k]['runs']+=1;groups[k]['target_mentions']+=int(a['target_mentioned']);groups[k]['self_report_lexical_candidates']+=int(a['self_report_lexical_candidate']);groups[k]['quantum_present']+=int(a['quantum_mentioned']);groups[k]['repeat_stops']+=int(r['generation']['stop_reason']=='repeated_8gram_3times')
 rows.append({'scope':k,'alpha':r['alpha'],'concept':r['concept'],'category':a['category'],'target':a['target_mentioned'],'self_report_candidate':a['self_report_lexical_candidate'],'quantum':a['quantum_mentioned'],'tokens':r['generation']['tokens'],'stop':r['generation']['stop_reason'],'text':r['generation']['text']})
s={'complete':True,'validated':True,'cases':40,'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'baseline_matches_morning':x['baseline_matches_morning_token_ids'],'baseline_unchanged_after_all':x['baseline_unchanged_after_all'],'decode_hook_calls_checked':decode_calls,'max_relative_norm_writeback_error':maxnormerror,'groups':groups,'rows':rows}
(R/'experiment4_high_dose_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2))
lines=['# 实验4：强剂量与持续注入——全部真实生成文本','',time.strftime('%Y-%m-%d %H:%M:%S %z'),'','GPU仅用Spark；模型权重不变。方向为N=100 J-lens，包含Final RMSNorm权重。α以各层干净prompt末位置的L2范数为单位，生成期沿用相同固定幅度。随机方向对面包/火锅/大象三个单位概念方向的张成空间正交。逐层逐步预设增量范数相等，BF16写回有舍入误差。',f'40格均完成；核验了{decode_calls}次生成步hook。实际增量范数相对预设值的最大偏差为{100*maxnormerror:.3f}%。',f'新基线与上午token IDs相同：{x["baseline_matches_morning_token_ids"]}；全部实验后的无注入基线与开头相同：{x["baseline_unchanged_after_all"]}。','', '## 无注入基线','','```text',x['baseline']['text'],'```','', '## 读表说明','', '自述候选只按目标词与报告措辞共同出现粗筛，不能证明觉察；必须结合原文。直接出现概念词、真正有报告型句式、重复崩坏是不同现象。EOS输出不补字；达到128 tokens或重复停止的片段明确标注，不伪称无限完整回答。','', '|范围|α|方向|目标字面命中|自述候选|量子纠缠|词元数|停止原因|','|---|---:|---|---|---|---|---:|---|']
for r in rows:lines.append(f'|{r["scope"]}|{r["alpha"]}|{r["concept"]}|{r["target"]}|{r["self_report_candidate"]}|{r["quantum"]}|{r["tokens"]}|{r["stop"]}|')
for i,r in enumerate(rows,1):
 lines+=['',f'## {i}. {r["scope"]} · {r["concept"]} · α={r["alpha"]}',f'停止原因：{r["stop"]}；生成{r["tokens"]} tokens。','','```text',r['text'],'```']
lines+=['','## 结束后的无注入基线','','```text',x['baseline_after_all']['text'],'```']
(R/'experiment4_high_dose_texts.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'complete':True,'groups':groups,'max_relative_norm_writeback_error':maxnormerror,'decode_hook_calls_checked':decode_calls},ensure_ascii=False))
