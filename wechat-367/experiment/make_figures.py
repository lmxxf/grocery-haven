import os
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;s=json.loads((R/'summary.json').read_text());rows=s['by_layer'];x=[r['layer']for r in rows]
plt.rcParams.update({'font.family':['WenQuanYi Micro Hei','DejaVu Sans'],'svg.fonttype':'none','axes.unicode_minus':False,'figure.facecolor':'white','axes.facecolor':'white'})
fig,ax=plt.subplots(figsize=(10,4.5));ax.plot(x,[r['kappa_gt1']for r in rows],label='留出 κ > 1',color='#1764b0');ax.plot(x,[r['kappa_gt10']for r in rows],label='留出 κ > 10',color='#c45121');ax.set(xlabel='Block 输出层 L0..L63',ylabel='成分轴数量（每层5120）',ylim=(0,5300),title='ICA-Lens：留出自然文本的重尾轴数量');ax.grid(alpha=.2);ax.legend();fig.text(.5,.01,'高 κ 是统计指纹，不等于清晰概念数；固定50步 FastICA',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(R/'kurtosis_by_layer.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(10,4.5))
for name,label,color in [('bank','bank：银行 / 河岸','#1764b0'),('apple_en','apple：水果 / 公司','#c45121'),('苹果_zh','苹果：水果 / 公司','#238454')]:ax.plot(x,[r['polysemy'][name]['heldout_accuracy']for r in rows],label=label,color=color,alpha=.8)
ax.axhline(.5,color='#777777',linestyle='--',linewidth=1);ax.set(xlabel='Block 输出层',ylabel='单轴阈值分类留出正确比例',ylim=(-.03,1.05),title='目标词位置的上下文词义对比（每层8个留出例）');ax.legend(loc='lower right');ax.grid(alpha=.2);fig.text(.5,.01,'每义8例选轴/阈值标定，4例留出。跨层预测不是独立样本。',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,1));fig.savefig(R/'polysemy_by_layer.svg');plt.close(fig)
