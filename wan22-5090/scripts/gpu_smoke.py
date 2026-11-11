import json,time,sys,traceback
from pathlib import Path
import torch
R=Path(r'C:\AI\Wan22-ComfyUI');torch.manual_seed(20261111)
info={'python':sys.version,'torch':torch.__version__,'cuda':torch.version.cuda,'device':torch.cuda.get_device_name(0),'capability':list(torch.cuda.get_device_capability(0)),'architectures':torch.cuda.get_arch_list()}
assert info['capability']==[12,0]
assert tuple(map(int,torch.version.cuda.split('.')[:2]))>=(12,8)
a=torch.randn(256,256,device='cuda');b=torch.randn(256,256,device='cuda');aa=a.to(torch.float8_e4m3fn);bb=b.to(torch.float8_e4m3fn);scale=torch.ones((),device='cuda',dtype=torch.float32)
c=torch._scaled_mm(aa,bb.T,scale_a=scale,scale_b=scale,out_dtype=torch.bfloat16);c=c[0]if isinstance(c,tuple)else c
reference=aa.float()@bb.float().T;err=float((c.float()-reference).norm()/reference.norm());assert torch.isfinite(c).all()and err<.02
q=torch.randn(1,8,512,128,device='cuda',dtype=torch.bfloat16);y=torch.nn.functional.scaled_dot_product_attention(q,q,q);assert torch.isfinite(y).all()
info.update(fp8_scaled_mm_finite=True,fp8_scaled_mm_relative_error=err,sdpa_finite=True)
(R/'logs/gpu_smoke.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
