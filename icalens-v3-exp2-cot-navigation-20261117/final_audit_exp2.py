"""Cache-only final audit. Append corrections; never rewrite the chronological ledger."""
from common_exp2 import *
import sys,json,math,re
from collections import Counter
import numpy as np
from analyze_exp2 import aggregate,serial_clean

def entropy_from_decode(record,f):
 if 'H_bits_head_batch'not in f:f['H_bits_head_batch']=f['H_bits'].copy()
 for e in record['decode_events']:f['H_bits'][e['state_position']]=e['H_bits']
 term=record['terminal_prediction'];f['H_bits'][term['state_position']]=term['H_bits'];f['H_generated_source_cached']=np.array(1,dtype='int8')
 np.savez_compressed(H/record['id']/'metrics.npz',**f)
 kinpath=H/record['id']/'kinematics.npz';kin=dict(np.load(kinpath));kin['H_bits_head_batch']=f['H_bits_head_batch'];kin['H_bits']=f['H_bits'];kin['H_generated_source_cached']=f['H_generated_source_cached'];np.savez_compressed(kinpath,**kin)

def run():
 names=read(R/'completed_cases.json');records=[read(R/'traces'/f'{n}.json')for n in names];lookup={r['id']:r for r in records};features={r['id']:dict(np.load(H/r['id']/'metrics.npz'))for r in records};scope=read(R/'scope.json');null=read(R/'calibration.json')
 for r in records:entropy_from_decode(r,features[r['id']])
 summary=aggregate(records,features,scope,null);save('summary.json',serial_clean(summary))
 # Update archived per-token entropy fields to the actual single-step decoding record.
 for r in records:
  path=R/'traces'/f'{r["id"]}_navigation.json'
  if path.exists():
   trace=read(path)
   for rows in trace['layers'].values():
    for row in rows:row['H_next_bits']=float(features[r['id']]['H_bits'][row['t']])
   save(f'traces/{r["id"]}_navigation.json',trace)
 for path in (R/'events').glob('*.json'):
  ident=next((n for n in names if path.stem.startswith(n+'_')),None)
  if ident:
   rows=read(path)
   for row in rows:row['H_next_bits']=float(features[ident]['H_bits'][row['t']])
   save(str(path.relative_to(R)),rows)
 if (R/'vertical_sections.json').exists():
  data=read(R/'vertical_sections.json')
  for section in data:
   for row in section['layers']:row['H_next_bits']=float(features[section['case']]['H_bits'][row['t']])
  save('vertical_sections.json',data)
 # Compare original no-effect EOS arms over exactly the same token positions.
 matched=[]
 for name in ['sum','mul']:
  a=lookup['port_'+name+'_natural'];b=lookup['port_'+name+'_forced'];P=a['prompt_length'];end=P+min(len(a['generated_ids']),len(b['generated_ids']));start=P+b['forced_at_generated_index']+5;ix=np.arange(start,end);fa=features[a['id']];fb=features[b['id']];m={}
  for key in ['s_geo','kappa_geo','erank_dir','zmax_positive','top20_energy','deltaC_10']:
   m[key]=dict(n=len(ix),natural_mean=float(fa[key][32,ix].mean()),forced_mean=float(fb[key][32,ix].mean()),max_abs_diff=float(np.nanmax(np.abs(fa[key][:,ix]-fb[key][:,ix]))))
  m['H_bits']=dict(n=len(ix),natural_mean=float(fa['H_bits'][ix].mean()),forced_mean=float(fb['H_bits'][ix].mean()),max_abs_diff=float(np.max(np.abs(fa['H_bits'][ix]-fb['H_bits'][ix]))));matched.append(dict(pair=name,start=int(start),end=int(end),metrics=m))
 save('port_matched_window_audit.json',matched)
 # Full layer scan of the scratch-to-answer speed claim, instead of selecting L32 only.
 phases=[];counts=[]
 for r in records:
  if r['group']!='reason':continue
  f=features[r['id']];s=scope[r['id']];c=s['closing_parenthesis_position'];before=np.arange(max(5,s['start']+2),c);after=np.arange(c+1,s['end']);row=dict(id=r['id'],n_before=len(before),n_after=len(after),layers=[])
  for l in range(64):
   a=float(f['s_geo'][l,before].mean());b=float(f['s_geo'][l,after].mean());row['layers'].append(dict(layer=l,s_before=a,s_after=b,ratio=b/a))
  phases.append(row)
 for l in range(64):counts.append(dict(layer=l,smaller=sum(r['layers'][l]['ratio']<1 for r in phases),total=len(phases),mean_ratio=float(np.mean([r['layers'][l]['ratio']for r in phases]))))
 save('phase_all_layers.json',dict(cases=phases,layer_counts=counts))
 # Paired sign agreement between signed, conditional-positive and full-positive C measures.
 positive=[]
 for group in ['rail_clean','reason']:
  rows=[row for row in summary['cases']if row['group']==group];out=dict(group=group)
  for tau in [10,30,50]:
   measures={}
   for mode in ['deltaC','deltaCpos','deltaCposfull']:
    vals=[]
    for row in rows:
     r=lookup[row['id']];s=scope[r['id']];ix=np.arange(max(5,s['start']+2),s['end']);vals.append(float(features[r['id']][f'{mode}_{tau}'][32,ix].mean()))
    measures[mode]=float(np.mean(vals))
   out[str(tau)]=measures
  positive.append(out)
 save('positive_half_comparison.json',positive)
 # Inspect the actual EOS intervention after the semantic answer, without pretending it is a loop.
 forced=lookup['port_eos_direct_forced'];f=features[forced['id']];P=forced['prompt_length'];arm=P+forced['forced_at_generated_index'];before=np.arange(P,arm);after=np.arange(arm+5,forced['total_tokens']);counts_islands=Counter(map(int,f['top5_axis'][32,after,0]));port=dict(before_rank=float(f['erank_dir'][32,before].mean()),after_rank=float(f['erank_dir'][32,after].mean()),before_H=float(f['H_bits'][before].mean()),after_H=float(f['H_bits'][after].mean()),after_main_islands=len(counts_islands),top3_coverage=sum(n for _,n in counts_islands.most_common(3))/len(after),top4_coverage=sum(n for _,n in counts_islands.most_common(4))/len(after),extra_tokens=forced['actual_extra_after_arm'],genuine_eos_proposal=forced['forced_reason']=='eos_proposal')
 save('real_eos_final_metrics.json',port)
 # Marker positions are audited against their own trajectory rather than labelled curvature spikes by fiat.
 marker_audit=[]
 for ident,t in [('reason_05',127),('correction_mul49',149)]:
  r=lookup[ident];f=features[ident];s=scope[ident];ix=np.arange(max(5,s['start']+2),s['end']);z=np.load(H/ident/'ica_z.npy',mmap_mode='r');old=int(f['top5_axis'][32,t-1,0]);new=int(f['top5_axis'][32,t,0]);marker_audit.append(dict(case=ident,t=t,token=r['token_text'][t],kappa_g=float(f['kappa_geo'][32,t]),within_case_kappa_percentile=float(np.mean(f['kappa_geo'][32,ix]<=f['kappa_geo'][32,t])*100),old_axis=old,new_axis=new,old_z_before=float(z[32,t-1,old]),old_z_now=float(z[32,t,old]),new_z_before=float(z[32,t-1,new]),new_z_now=float(z[32,t,new]),top20=float(f['top20_energy'][32,t]),deltaC10=float(f['deltaC_10'][32,t])))
 save('marker_switch_audit.json',marker_audit)
 # A second static plot explicitly uses the real EOS arm; retain the initial figure unchanged.
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,axes=plt.subplots(4,1,figsize=(11,9),sharex=True)
 for ident,color in [('reason_01','#d97706'),('port_eos_direct_forced','#0284c7'),('cycle_positive_control','#8b5cf6')]:
  r=lookup[ident];ff=features[ident];ix=np.arange(r['prompt_length'],r['total_tokens']);x=ix-r['prompt_length']
  for ax,key in zip(axes,['s_geo','kappa_geo','erank_dir','zmax_positive']):ax.plot(x,ff[key][32,ix],lw=1,label=ident,color=color)
 for ax,label in zip(axes,['Geodesic step','Geodesic curvature','5-step tangent rank','Positive peak z']):ax.set_ylabel(label);ax.grid(alpha=.2)
 axes[0].legend(fontsize=8);axes[-1].set_xlabel('Generated token index (L32)');fig.tight_layout();fig.savefig(R/'navigation_real_eos_L32.svg');plt.close(fig)
 val=read(R/'validation.json');raw_error=val['entropy_max_cached_vs_recomputed'];val.update(entropy_primary_generated_source='actual decode_events and terminal_prediction; prefill-only earlier positions use chunked readout',entropy_generated_max_error_after_sync=max(abs(float(features[r['id']]['H_bits'][e['state_position']])-e['H_bits'])for r in records for e in r['decode_events']),all_light_files_under_10MB=not any(p.is_file()and p.stat().st_size>10_000_000 for p in R.rglob('*')));assert val['entropy_generated_max_error_after_sync']==0.;assert val['all_light_files_under_10MB'];save('validation.json',val)
 text=f"模型已经释放；本节全部只读/重算缓存，没有重载27B、没有补生成。\n\n**熵的测量修正**：从生成残差批量过lm_head，与当时单步logits的BF16 GEMM形状不同，H最大差{raw_error:.6f} bit。现在所有生成位置优先用decode_events/terminal_prediction原始H；批量复算值另保留H_bits_head_batch。更新metrics、summary、逐token JSON后，与生成日志最大误差为0；s、κ_g、rank、ICA坐标均未改变。\n\n**自然/强制窗口对齐**：前一节port表保留了自然臂更长的整个尾段，两种长度均值不能解释成干预效应。现将sum/mul限定到共同前缀相同位置；结果：\n\n```json\n"+json.dumps(matched,ensure_ascii=False,indent=2)+"\n```\n\n**正半轴实测对账（L32，按case等权）**：\n\n```json\n"+json.dumps(positive,ensure_ascii=False,indent=2)+"\n```\n\n**括号内→括号外，全层扫一遍**：\n\n|层|步长变小案例数|案例总数|答案/草稿步长比均值|\n|---|---|---|---|\n"
 for l in [0,10,16,20,24,32,40,48,56,63]:q=counts[l];text+=f"|{l}|{q['smaller']}|{q['total']}|{q['mean_ratio']:.5f}|\n"
 text+='\n这批Qwen3.8-27B裸续写没有复现“出括号普遍收步”；L32只有1/8、L63为3/8。括号外片段只有1~23 token，rank5窗口还混有前面的草稿，不能按“独立答案阶段的全局维数”解读。\n\n**两处纠错的切岛读数**：\n\n```json\n'+json.dumps(marker_audit,ensure_ascii=False,indent=2)+'\n```\n\n纠错词是否真是κ峰，以上给出在自身轨迹的百分位；不把“出现重新/更严谨”自动等同于曲率暴涨。\n'
 text+=f"\n**真正EOS干预的结局**：正确短答42后阻断EOS，继续96 token。rank5 {port['before_rank']:.4f}→{port['after_rank']:.4f}，原始H {port['before_H']:.4f}→{port['after_H']:.4f} bits；尾段经过{port['after_main_islands']}根主岛轴，Top3/Top4覆盖率{port['top3_coverage']:.2%}/{port['top4_coverage']:.2%}。未复现固定三四礁石的低秩港口；实际走向猜测题目笔误、把加法改想成乘法。数字重复正对照也没遵守原42，而是生成44串；这证明它有重复，不证明它停在原答案岛。\n\n新图用真正EOS干预作蓝线，保留初图不覆盖：![实际EOS干预](navigation_real_eos_L32.svg)。\n"
 text+='\n**岛名本身的意外**：同一个生成“明月”位置，L32主岛C1909词牌为“…、查看答案解析、点击上方蓝字”，L40才同时出现C1513（白居易、诗句、诗词）与C2978（moon、月亮、lunar）。高z证明当前坐标尖峰，不保证Top1就是一个漂亮的主题名词；本轮没有手工把模板/标点岛改叫诗意岛。\n'
 append('Step 5 末审与修正｜同窗、原始熵、全层步长、实际EOS',text)
 final='本轮可复现的落点：\n\n1. κ阈值掩码比例须扣基线；L32为64.0625%。推理中的负ΔC10不能直接叫深海：最负尖峰例仍有z_max=7.006、Top20=6.86%，主岛C3605本身κ=6.56。置换轴标签后ΔC回到约0，而尖峰不变。\n2. 首段熟诗比多步推理更尖：L32 z_max 18.97 vs 10.68，Top20 13.49% vs 8.53%；两组按本轮三项参照均无高斯平摊样本。更像稀释但不断岛的分布式混航，没有拍到“算完才从完全平海出水”。\n3. 真实词牌能看到重新C2436、数学C785、改用C1007等桥接，同时大量标点/换行/模板岛参与。纠错不呈统一“弃岛落海”或“两大岛恒定拔河”的固定模板，逐步交叉读数保留在窗口里。\n4. 这批未复现括号外普遍收步，也未复现阻断EOS后必然低秩港口。真正阻断反而诱发虚构笔误及新分支；不要把无效EOS臂和实际干预混为一谈。\n\n文件入口：README.md、summary.json、traces/、island_labels/、events/、vertical_sections.json、phase_all_layers.json、real_eos_final_metrics.json。原始残差、ica_z.npy和metrics.npz全部留在重数据目录。'
 append('最后读数｜四个悬念得到什么',final)
 readme=['# ICA-Lens v3 思维链航海实验','', '按时间读 [DevHistory.md](DevHistory.md)，最后的Step 5给出测量修正和核心读数；不是论文报告。','', f'{len(records)}条真实裸文本轨迹、全64层，一次完整27B驻留；最后缓存核对不重载模型。','', '- L32：熟诗/推理正极峰值18.97/10.68；Top20能量13.49%/8.53%；本轮未出现高斯平摊深海。','- 负ΔC并不等于无尖峰；轴标签置换和正半轴对账已完成。','- 括号外收步未普遍复现：L32为1/8，L63为3/8。','- 真正屏蔽EOS后追加96 token，rank5升至4.22、经过53根主岛轴；未形成固定三四岛港口。','', '看：summary.json、phase_all_layers.json、port_matched_window_audit.json、real_eos_final_metrics.json、mask_permutation_ablation.json、traces/、events/、island_labels/、vertical_sections.json。','',f'大数组只在 `{H}`。轻量目录无超过10MB文件。','', '![真实EOS干预](navigation_real_eos_L32.svg)','', '复现：bash run_all.sh。末审入口：`final_audit_exp2.py`，仅用已保存数据。']
 (R/'README.md').write_text('\n'.join(readme)+'\n');print('FINAL_AUDIT_PASS',len(records),'cases', 'H error',val['entropy_generated_max_error_after_sync'])
if __name__=='__main__':run()
