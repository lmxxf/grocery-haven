import sys,json,gc,time
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'upstream'))
import torch
from jlens import JacobianLens
from stream_fitting import matrix_stats,pair_stats
torch.set_num_threads(8)
cfg=json.loads(Path('/home/lmxxf/work/models/Qwen3.8-27B-FP8/config.json').read_text())['text_config']
a=JacobianLens.load(str(R/'fit_even/lens_local_n1.pt'))
b=JacobianLens.load(str(R/'early_odd/lens_local_n1.pt'))
assert a.n_prompts==b.n_prompts==1
lenses={1:a,2:JacobianLens.merge([a,b])}
# Only take N=4 if both local N=2 snapshots already exist. Never wait for it.
if (R/'fit_even/lens_local_n2.pt').exists() and (R/'early_odd/lens_local_n2.pt').exists():
 lenses[4]=JacobianLens.merge([JacobianLens.load(str(R/'fit_even/lens_local_n2.pt')),JacobianLens.load(str(R/'early_odd/lens_local_n2.pt'))])
stats={};prev=None
for n,lens in lenses.items():
 lens.save(str(R/f'lens_n{n}.pt'))
 rows={}
 for l,J in lens.jacobians.items():
  s=matrix_stats(J);s.update(source_layer_type=cfg['layer_types'][l],next_layer_type=cfg['layer_types'][l+1])
  if prev:
   P=prev.jacobians[l];s.update(pair_stats(J,P))
  rows[l]=s
 stats[n]={'n_prompts':n,'layers':rows,'prompt_indices':list(range(n))};prev=lens
(R/'early_convergence_summary.json').write_text(json.dumps(stats,indent=2))
(R/'early_snapshot_manifest.json').write_text(json.dumps({'created_time':time.time(),'Ns':list(lenses),'n1_source':'formal even worker checkpoint on prompt 0 (not the dim_batch1 smoke)','n2_sources':['prompt 0 English','prompt 1 Chinese'],'method':'official JacobianLens.merge, input portable FP16 checkpoints promoted to FP32; full matrices'},indent=2))
print('EARLY_MERGE_DONE',list(lenses),flush=True)
