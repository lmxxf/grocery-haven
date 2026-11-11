import os,json,time,traceback,importlib.metadata as md
from pathlib import Path
R=Path(r'C:\AI\Wan22-ComfyUI');os.environ['TRITON_CACHE_DIR']=str(R/'cache/triton');os.environ['TORCHINDUCTOR_CACHE_DIR']=str(R/'cache/inductor')
os.environ.setdefault('TRITON_DEFAULT_FP_FUSION','1')
import torch
import triton
import triton.language as tl
@triton.jit
def add_kernel(a,b,c,N:tl.constexpr,BLOCK:tl.constexpr):
 i=tl.program_id(0)*BLOCK+tl.arange(0,BLOCK);tl.store(c+i,tl.load(a+i,i<N)+tl.load(b+i,i<N),i<N)
torch.manual_seed(20261111);a=torch.randn(1024,device='cuda');c=torch.empty_like(a);add_kernel[(1,)](a,a,c,1024,1024);assert torch.allclose(c,a+a)
from sageattention import sageattn
q=torch.randn(1,40,4096,128,device='cuda',dtype=torch.bfloat16);k=torch.randn_like(q);v=torch.randn_like(q)
fns={'sdpa':lambda:torch.nn.functional.scaled_dot_product_attention(q,k,v),'sage':lambda:sageattn(q,k,v,tensor_layout='HND',is_causal=False)};ys={};timings={}
with torch.inference_mode():
 for name,fn in fns.items():
  for i in range(3):y=fn()
  torch.cuda.synchronize();start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True);start.record()
  for i in range(10):y=fn()
  end.record();torch.cuda.synchronize();timings[name]=start.elapsed_time(end)/10;ys[name]=y.float();assert torch.isfinite(y).all()
rel=float((ys['sage']-ys['sdpa']).norm()/ys['sdpa'].norm());maxabs=float((ys['sage']-ys['sdpa']).abs().max());assert rel<.08
result={'state':'pass','torch':torch.__version__,'cuda':torch.version.cuda,'triton_windows':md.version('triton-windows'),'sageattention':md.version('sageattention'),'shape':list(q.shape),'dtype':'bfloat16','triton_add_pass':True,'relative_l2_sage_vs_sdpa':rel,'max_abs_sage_vs_sdpa':maxabs,'cuda_event_ms_mean10':timings,'note':'warm attention microbenchmark, not end-to-end video speed','time':time.time()}
(R/'logs/attention_benchmark.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
