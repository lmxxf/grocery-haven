"""Spark-only cached continuation validation on tiny models before real runs."""
import ast,torch,numpy as np,math,json
import torch.nn.functional as F
from transformers import GPT2Config,GPT2LMHeadModel,GPTNeoXConfig,GPTNeoXForCausalLM
from transformers.cache_utils import DynamicCache
from pathlib import Path
assert 'GB10' in torch.cuda.get_device_name()
source=ast.parse(Path(__file__).with_name('run_reproduction.py').read_text());nodes=[n for n in source.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ['ent','geom','baseline','suffix']]
results=[]
for isgpt in [True,False]:
 torch.manual_seed(361)
 m=(GPT2LMHeadModel(GPT2Config(vocab_size=100,n_positions=64,n_embd=32,n_layer=4,n_head=4)) if isgpt else GPTNeoXForCausalLM(GPTNeoXConfig(vocab_size=100,hidden_size=32,num_hidden_layers=4,num_attention_heads=4,intermediate_size=64,max_position_embeddings=64))).cuda().eval();m.set_attn_implementation('sdpa')
 base=m.transformer if isgpt else m.gpt_neox;blocks=base.h if isgpt else base.layers;norm=base.ln_f if isgpt else base.final_layer_norm;head=m.get_output_embeddings();site=1;L=4
 scope=dict(torch=torch,np=np,F=F,math=math,DynamicCache=DynamicCache,isgpt=isgpt,m=m,base=base,blocks=blocks,norm=norm,head=head,site=site,L=L)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pipeline>','exec'),scope)
 ids=list(range(10,26));k=10;X,H,z,cache=scope['baseline'](ids,k);ee,zz=scope['suffix'](X,cache,k,torch.zeros(3,32,device='cuda'));err=float((zz.cpu()-z).abs().max());assert err<.002,err
 # A nonzero local edit must agree with replaying the entire original prefix.
 delta=torch.randn(1,32,device='cuda')*.03;ee,zz=scope['suffix'](X,cache,k,delta)
 def hook(mod,a,o):return o+torch.nn.functional.pad(delta[:,None],(0,0,k,0))
 h=blocks[site].register_forward_hook(hook)
 with torch.inference_mode():full=m(torch.tensor([ids[:k+1]],device='cuda'),use_cache=False).logits[0,-1]
 h.remove();editerr=float((zz[0]-full).abs().max());assert editerr<.002,editerr
 results.append(dict(model='GPT2' if isgpt else 'GPTNeoX',zero_delta_max_logit_error=err,nonzero_delta_vs_full_replay_max_error=editerr));print(results[-1],flush=True)
Path(__file__).with_name('suffix_validation.json').write_text(json.dumps(results,indent=2))
