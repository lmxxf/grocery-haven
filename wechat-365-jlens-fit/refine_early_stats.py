"""CPU-only numerical verification of early diagnostics; no lens changes."""
import sys,json,time
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'upstream'))
import torch
from stream_fitting import pair_stats,matrix_stats
torch.set_num_threads(4)
a=torch.load(R/'fit_even/lens_local_n1.pt',map_location='cpu',mmap=True,weights_only=True)
b=torch.load(R/'early_odd/lens_local_n1.pt',map_location='cpu',mmap=True,weights_only=True)
p=R/'early_convergence_summary.json';stats=json.loads(p.read_text())
for l in range(63):
 P=a['J'][l].float();J=(P+b['J'][l].float())/2
 s=pair_stats(J,P);assert -1-1e-12<=s['cosine_to_previous_snapshot']<=1+1e-12
 stats['2']['layers'][str(l)].update(s)
 del P,J
stats['2']['diagnostic_precision']='FP64 blockwise cosine and difference reductions; reconstructed unrounded FP32 weighted mean from original FP16 worker checkpoints; no model/GPU used'
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(stats,indent=2));tmp.replace(p)
c=[s['cosine_to_previous_snapshot']for s in stats['2']['layers'].values()]
print('REFINED_COSINES',sum(c)/len(c),min(c),max(c),flush=True)
