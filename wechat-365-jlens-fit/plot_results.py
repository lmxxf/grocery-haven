import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
cp=R/'convergence_summary.json'
if not cp.exists():cp=R/'early_convergence_summary.json'
if not cp.exists():raise SystemExit(0)
c=json.loads(cp.read_text())
fig,ax=plt.subplots(figsize=(8,4))
for name,label in [('even','English (master)'),('odd','Chinese (slave)')]:
 p=R/f'convergence_{name}.jsonl'
 if p.exists():
  rows=[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
  ax.loglog([r['local_N']for r in rows],[r['mean_rel_change']for r in rows],'.-',label=label)
ax.set(xlabel='Prompts per worker (local N)',ylabel='Relative running-mean update',title='Local running-mean updates (not a proof of convergence)');ax.legend();ax.grid(alpha=.25);fig.tight_layout();fig.savefig(R/'convergence.svg');plt.close(fig)
final=c.get('100',list(c.values())[-1])['layers'];ls=[int(l)for l in final]
fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
for typ,color in [('linear_attention','#2166ac'),('full_attention','#b2182b')]:
 sub=[l for l in ls if final[str(l)]['source_layer_type']==typ]
 axes[0].scatter(sub,[final[str(l)]['frobenius_over_sqrt_d']for l in sub],label='source '+typ,c=color,s=20)
axes[0].set(ylabel='||J||F / sqrt(d)');axes[0].legend()
axes[1].plot(ls,[final[str(l)]['diagonal_energy_fraction']for l in ls],'.-');axes[1].set(xlabel='Source block output index',ylabel='Diagonal energy fraction')
fig.suptitle('Full-width Jacobian structure (source-type association only)');fig.tight_layout();fig.savefig(R/'layer_structure.svg');plt.close(fig)
p=R/'evaluation_results.json'
if not p.exists():p=R/'early_evaluation_results.json'
if p.exists():
 e=json.loads(p.read_text());fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
 for ax,group in zip(axes,['multihop','multilingual']):
  names=list(e['stages']);x=list(range(len(names)))
  for k in [1,5,10]:ax.plot(x,[100*e['stages'][n]['metrics'][group][f'pass@{k}']for n in names],'.-',label=f'pass@{k}')
  ax.set_xticks(x,names,rotation=35);ax.set(title=group,ylabel='Eligible-item mean hit fraction (%)');ax.legend();ax.grid(alpha=.25)
 fig.tight_layout();fig.savefig(R/'lens_quality.svg');plt.close(fig)
