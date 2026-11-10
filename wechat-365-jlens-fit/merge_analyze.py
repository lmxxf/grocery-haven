import sys,json,gc,math,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'upstream'))
import torch
from jlens import JacobianLens
from stream_fitting import matrix_stats,pair_stats
torch.set_num_threads(8)
cfg=json.loads(Path('/home/lmxxf/work/models/Qwen3.8-27B-FP8/config.json').read_text())['text_config']
stats={};previous=None
for n in [1,2,4,10,20,50,100]:
 even=JacobianLens.load(str(ROOT/'fit_even'/f'lens_local_n{max(1,n//2)}.pt'))
 if n==1:lens=even
 else:
  odd=JacobianLens.load(str(ROOT/'fit_odd'/f'lens_local_n{n//2}.pt'))
  lens=JacobianLens.merge([even,odd]);del odd
 path=ROOT/f'lens_n{n}.pt';lens.save(str(path))
 layers={}
 for l,J in lens.jacobians.items():
  s=matrix_stats(J);s['source_layer_type']=cfg['layer_types'][l];s['next_layer_type']=cfg['layer_types'][l+1]
  if previous:
   P=previous.jacobians[l];s.update(pair_stats(J,P))
  layers[l]=s
 stats[n]={'n_prompts':n,'layers':layers}
 previous=lens;del even;gc.collect()
 print('MERGED',n,flush=True)
(ROOT/'convergence_summary.json').write_text(json.dumps(stats,indent=2))
# Full precision matrices are held by official lens object; the portable files
# use the official save() default FP16 convention, recorded in the report.
import shutil
shutil.copyfile(ROOT/'lens_n100.pt',ROOT/'Qwen3.8-27B_jacobian_lens.pt')
