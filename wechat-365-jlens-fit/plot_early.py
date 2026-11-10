import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'WenQuanYi Micro Hei','svg.fonttype':'none','axes.unicode_minus':False})
e=json.loads((R/'early_evaluation_results.json').read_text());c=json.loads((R/'early_convergence_summary.json').read_text())
names=['vanilla','n1','n2'];labels=['直接读出','N=1 英文','N=2 中英'];colors=['#7c8799','#2979bb','#e88628']
fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
for ax,group,title in zip(axes,['multihop','multilingual'],['多跳概念（84/93题可评分）','多语言概念（107题）']):
 x=np.arange(3);w=.24
 for j,k in enumerate([1,5,10]):
  v=[e['stages'][n]['metrics'][group][f'pass@{k}']*100 for n in names]
  bars=ax.bar(x+(j-1)*w,v,w,label=f'pass@{k}',color=['#345c89','#67a3c8','#a7ccd9'][j])
  ax.bar_label(bars,fmt='%.1f',fontsize=8,padding=2)
 ax.set_xticks(x,labels);ax.set(title=title,ylim=(0,80));ax.legend(frameon=False,ncol=3,fontsize=8);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
axes[0].set_ylabel('跨层最佳词元命中率（%）')
fig.suptitle('早期镜头并未单调提分：单样本、双样本都还不能叫“收敛”',fontsize=14)
fig.text(.5,.015,'官方题集的Qwen词表适配；排除无单token形式的概念；并列取最优名次。不是答题正确率。',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(R/'early_lens_quality.svg');fig.savefig('/tmp/365-early-quality.png',dpi=130);plt.close(fig)
representatives=[r for r in e['stages']['vanilla']['items'] if r['group']=='representative']
fig,axes=plt.subplots(4,2,figsize=(11,12))
for ax,row in zip(axes.flat,representatives):
 case=row['name'];concept=next(iter(row['min_ranks']))
 for n,col,label in zip(names,colors,labels):
  q=next(v for v in e['stages'][n]['items']if v['name']==case)
  xs=sorted(map(int,q['layers']));ys=[q['layers'][str(l)]['ranks'][concept]for l in xs]
  ax.plot(xs,ys,label=label,c=col,lw=1.35)
 ax.set_yscale('log');ax.set_ylim(300000,.7);ax.set(title=f'{case} · {concept}',xlabel='层号（block输出，0起）',ylabel='词元Rank，越小越前');ax.grid(alpha=.18)
axes[0,0].legend(frameon=False,fontsize=8)
fig.suptitle('8道代表题：同一个末词位置，查看全部64层',fontsize=15)
fig.text(.5,.005,'注意：Rank只追踪标题中的指定词元及表面变体；同义概念可能以另一种语言出现。',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.025,1,.96));fig.savefig(R/'early_rank_paths.svg');plt.close(fig)
fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
for n,col,label in zip(['1','2'],colors[1:],labels[1:]):
 rows=c[n]['layers'];ls=sorted(map(int,rows));axes[0].plot(ls,[rows[str(l)]['frobenius_over_sqrt_d']for l in ls],label=label,c=col)
rows=c['2']['layers'];ls=sorted(map(int,rows));axes[1].plot(ls,[rows[str(l)]['cosine_to_previous_snapshot']for l in ls],'.-',c='#744d9c',ms=3)
axes[0].set(ylabel='||J||F / √5120');axes[0].legend(frameon=False);axes[1].set(xlabel='源层输出索引（0..62）',ylabel='N=1 与 N=2 的矩阵余弦',ylim=(.6,1.01))
for ax in axes:ax.grid(alpha=.2)
fig.suptitle('加入一个中文样本，63层矩阵仍有较大变化',fontsize=14)
fig.text(.5,.01,'逐层余弦以FP64分块复核；63层等权均值0.81343。不等于已经统计收敛。',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(R/'early_snapshot_change.svg');plt.close(fig)
print('EARLY_SVG_DONE')
