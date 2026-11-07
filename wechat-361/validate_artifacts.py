"""CPU-only mathematical and saved-array integrity checks."""
import ast,json,math,hashlib,os
from pathlib import Path
import torch,numpy as np
import torch.nn.functional as F
R=Path(__file__).resolve().parent;A=Path(os.environ.get('CURVATURE_ARRAY_ROOT',str(R)));nodes=[x for x in ast.parse((R/'run_reproduction.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name in ['geom','ent']];ns=dict(torch=torch,F=F,math=math);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<geometry>','exec'),ns)
x=torch.tensor([[[0.,0.],[1.,0.],[1.,1.],[2.,1.],[2.,2.],[3.,2.]]],dtype=torch.float64);c=ns['geom'](x);assert torch.allclose(c[0,4:],torch.full((2,),math.pi/2,dtype=c.dtype))
a=.73;q=torch.tensor([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]],dtype=torch.float64);assert torch.allclose(ns['geom'](x@q*7+42)[0,4:],c[0,4:])
y=x.clone();y[0,0]=torch.tensor([1000.,-1000.]);assert torch.allclose(ns['geom'](y)[0,5],c[0,5])
h=ns['ent'](torch.log(torch.tensor([.5,.25,.25])));assert abs(float(h)-1.5)<1e-6
summary=dict(right_angle=True,scale_rotation_translation_invariant=True,C_endpoint_index_valid=True,entropy_known_distribution_bits=float(h),models={})
sha=hashlib.sha256((R/'run_reproduction.py').read_bytes()).hexdigest()
for model,L in [('gpt2-xl',48),('pythia-2.8b',32)]:
 e=json.loads((R/model/'environment.json').read_text());assert e['script_sha256']==sha
 info={}
 for ds in ['long','short']:
  d=np.load(A/model/f'observation_{ds}.npz');a=d['C_rad'];b=d['H_bits'];assert a.shape[0]==L and a.shape[1]==len(b);assert np.isfinite(a).all() and np.isfinite(b).all();assert a.min()>=0 and a.max()<=math.pi;assert b.min()>=0 and b.max()<=math.log2(e['config']['vocab_size'])+.001;assert d['endpoint'].min()>=5
  info[ds]=dict(shape=list(a.shape),n_entropy=len(b),finite=True)
 summary['models'][model]=info
(R/'validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
