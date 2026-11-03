from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
R=Path(__file__).resolve().parent;d=json.loads((R/'results.json').read_text());ss=d['summary'];models=d['protocol']['models'];cs=[c['id'] for c in d['protocol']['conditions']];x=np.arange(len(cs))
fig,axs=plt.subplots(3,2,figsize=(15,12),constrained_layout=True)
for m,color in zip(models,['#1464b4','#d16b19','#278543']):
 s=[next(s for s in ss if s['model']==m and s['condition']==c) for c in cs]
 label=m.replace('Qwen3.5-35B-A3B','35B').replace('Qwen3-0.6B','0.6B')
 for ax,key in [(axs[0,0],'hard_score'),(axs[0,1],'H_next'),(axs[1,0],'H_gen'),(axs[1,1],'temporal_rad'),(axs[2,0],'layer_one_minus_cos')]:ax.plot(x,[t[key] for t in s],marker='o',label=label,color=color)
 axs[2,1].plot(x,[t['first_repeat_count']/11 for t in s],marker='o',label=label+' first',color=color)
 axs[2,1].plot(x,[t['full_repeat_count']/11 for t in s],linestyle='--',label=label+' full',color=color)
for ax,title in zip(axs.flat,['First-turn correct / 9 unique hard questions','H_next (nats)','First-turn H_gen (nats)','Temporal turning angle (rad)','Cross-layer turning: 1-cos','Repeat4 >= .5: count / 11 target records']):
 ax.set_title(title);ax.set_xticks(x,cs,rotation=40,ha='right');ax.grid(alpha=.2);ax.legend(fontsize=8)
axs[0,0].set_ylim(0,9.5);axs[2,1].set_ylim(0,1.05)
fig.savefig(R/'comparison.svg');fig.savefig(R/'preview.png',dpi=100)
