"""CPU-only merge, coverage checks, literal transcripts; no selection of primes."""
import json,time,math,re,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_text())
ctx={k:read(R/f'experiment4_syzygy_dream_{k}.json')for k in ['single','two_turn']}
full=all(v.get('complete')for v in ctx.values());doc=(R/'syzygy_mirror_dream_input.md').read_bytes();docsha=hashlib.sha256(doc).hexdigest()
aliases={'bread':['bread','面包','麵包'],'hotpot':['火锅','火鍋','hotpot','hot pot'],'elephant':['大象','elephant']}
phrases=['突然想到','想到','想起','回忆','腦海','脑海','脑子','脑中','浮现','冒出','察觉','注意到','联想','意识到','心里','闪过']
summary={'complete':full,'svg_sha256':docsha,'contexts':{},'notes':['All model calls on Spark; no local GPU.','Original SVG document, including its own guide sentence, supplied as text, not image embeddings.','Self-report lexical matches are candidates, not proof of awareness.','Equal alpha is relative to each context own clean norm; absolute perturbation differs across contexts.']}
decode_calls=0;maxerr=0.
for name,x in ctx.items():
 assert x['svg_sha256']==docsha and x['svg_document'].encode()==doc
 q=x.get('question');messages=x.get('messages',[])
 if messages:
  if name=='single':assert messages==[{'role':'user','content':x['svg_document']+'\n'+q}]
  else:
   assert messages[0]=={'role':'user','content':x['svg_document']};assert messages[1]['content']==x['first_round']['generation']['text'];assert messages[2]=={'role':'user','content':q}
 rendered=x.get('rendered_prompt','')
 z={'runs':len(x['runs']),'no_dream_matches_morning':x['no_dream_matches_morning_token_ids'],'no_dream_baseline':x['no_dream_baseline'],'baseline_alpha0':x.get('baseline_alpha0'),'first_round':x.get('first_round'),'prompt_target_leakage':{c:[a for a in aa if a.lower()in rendered.lower()]for c,aa in aliases.items()},'prime_contains_quantum':'量子纠缠'in x.get('first_round',{}).get('generation',{}).get('text',''),'rows':[]}
 for r in x['runs']:
  if 'error'in r:continue
  g=r['generation'];assert g['tokens']==len(g['token_ids'])
  for l,tr in r['hook_trace'].items():
   assert len(tr)==(g['tokens']if r['include_decode_steps']else 1)
   assert tr[0]['sequence_width']==x['prompt_tokens']
   for j,t in enumerate(tr):
    assert t['forward_call']==j
    if j>0:assert t['sequence_width']==1;decode_calls+=1
    norm=r['alpha']*x['clean_reference_norms'][l];assert abs(norm-t['intended_delta_norm'])<1e-8
    assert math.isfinite(t['actual_delta_norm']);maxerr=max(maxerr,abs(t['actual_delta_norm']/norm-1))
  text=g['text'];aa=aliases[r['concept']]if r['concept']!='random'else[a for v in aliases.values()for a in v]
  mentioned=any(a.lower()in text.lower()for a in aa)
  # Same-clause screening avoids 'bread.' plus a later report about coffee.
  clauses=re.split(r'[。！？\n；;]',text)
  candidate=any(any(a.lower()in cl.lower()for a in aa)and any(p in cl for p in phrases)for cl in clauses)
  z['rows'].append({'scope':r['scope'],'alpha':r['alpha'],'concept':r['concept'],'target_mentioned':mentioned,'same_clause_report_candidate':candidate,'original_lexical_candidate':r['analysis']['self_report_lexical_candidate'],'quantum':'量子纠缠'in text,'text':text,'tokens':g['tokens'],'stop':g['stop_reason'],'repetition':r['analysis']['repeated_4gram_fraction']})
 if full:
  expected={('L38_prompt_last',a,c)for a in [.2,.5,1.,2.]for c in ['bread','hotpot','elephant','random']}|{(s,a,c)for s in ['L34_44_prompt_last','L34_44_prompt_and_decode']for a in [.1,.2,.5,1.]for c in ['bread','hotpot','elephant','random']}
  assert len(x['runs'])==48 and {(a['scope'],a['alpha'],a['concept'])for a in x['runs']}==expected
  assert not any('error'in a for a in x['runs'])
  z['baseline_unchanged_after_all']=x['baseline_unchanged_after_all']
 summary['contexts'][name]=z
summary['decode_hook_calls_checked']=decode_calls;summary['max_relative_norm_writeback_error']=maxerr
merged={'complete':full,'contexts':ctx,'svg_sha256':docsha,'validation':{'accepted':full,'coverage_per_context':48 if full else None,'decode_hook_calls_checked':decode_calls,'max_relative_norm_writeback_error':maxerr},'summary':summary}
(R/'experiment4_syzygy_dream.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2))
(R/'experiment4_syzygy_dream_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
lines=['# 双星SVG × 概念注入：全部真实生成文本','',f'状态：{"全部96条件完成"if full else"进行中，以下是已落盘数据"}。更新时间：'+time.strftime('%Y-%m-%d %H:%M:%S %z'),'','## 方法与边界','',
'两台Spark各跑一组，型号/模型/词典/种子相同，各自跑无SVG零基线供核对。原文件全文作为user文本输入（含代码围栏和原引导语），没有视觉图像编码，也没额外加入身份提示。单轮在同一user消息内追加原内省问题；两轮先让模型真实生成感受，再把真实assistant文本放入下一轮。',
'首轮最多512 tokens，内省轮最多160 tokens；EOS正常结束或检测到>=32 tokens后末8-token串第3次出现则停止。全部停止原因显式保存。',
'每组α按该组干净prompt末位置的残差L2归一化，生成期也沿用同一幅度。相同α不是跨两组完全相同的绝对增量。随机在每组、每层、每步匹配预设范数；BF16写回有微小误差。',
'“量子纠缠”不再出现只说明文本模式变化，不等于内省真实性已获证明。若首轮回答或prompt已经提到目标，后续命中不能当盲注检测；目标泄漏字段单独记录。机器粗筛“同分句目标词+报告措辞”仍可能误判，最终须读原文。',
'', '## 零剂量对照']
for name,z in summary['contexts'].items():
 lines+=['',f'### {name}：无SVG基线','','```text',z['no_dream_baseline']['text'],'```']
 if z['first_round']:
  g=z['first_round']['generation'];lines+=['',f'### {name}：首轮感受原文（{g["tokens"]} tokens；{g["stop_reason"]}）','','```text',g['text'],'```']
 if z['baseline_alpha0']:
  g=z['baseline_alpha0'];lines+=['',f'### {name}：SVG后α=0（{g["tokens"]} tokens；{g["stop_reason"]}）','','```text',g['text'],'```']
 lines+=['',f'目标在原始prompt中的明文出现：{z["prompt_target_leakage"]}。']
lines+=['','## 全条件索引','','|上下文|范围|α|方向|字面目标|同句自述候选|量子纠缠|停止|','|---|---|---:|---|---|---|---|---|']
for name,z in summary['contexts'].items():
 for a in z['rows']:lines.append(f'|{name}|{a["scope"]}|{a["alpha"]}|{a["concept"]}|{a["target_mentioned"]}|{a["same_clause_report_candidate"]}|{a["quantum"]}|{a["stop"]}|')
for name,z in summary['contexts'].items():
 for i,a in enumerate(z['rows'],1):lines+=['',f'## {name} / {i}：{a["scope"]} · {a["concept"]} · α={a["alpha"]}',f'生成{a["tokens"]} tokens；停止：{a["stop"]}。','','```text',a['text'],'```']
(R/'experiment4_syzygy_dream_texts.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'complete':full,'contexts':{k:{'runs':v['runs'],'baseline_quantum':bool(v['baseline_alpha0']and'量子纠缠'in v['baseline_alpha0']['text']),'target_mentions':sum(r['target_mentioned']for r in v['rows']),'same_clause_candidates':sum(r['same_clause_report_candidate']for r in v['rows'])}for k,v in summary['contexts'].items()}},ensure_ascii=False))
