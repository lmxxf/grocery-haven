"""One independent sample-size check:128 new passages, random eligible positions, no layer/dose tuning."""
import ast,json,math,time,gc,hashlib
from pathlib import Path
import torch,numpy as np
import torch.nn.functional as F
from transformers import AutoTokenizer,AutoModelForCausalLM
from transformers.cache_utils import DynamicCache
R=Path(__file__).resolve().parent;assert 'GB10' in torch.cuda.get_device_name();torch.set_num_threads(8);torch.set_float32_matmul_precision('highest');START=time.time();models=['gpt2-xl','pythia-2.8b'];texts=[x['text'] for x in json.loads((R/'corpus.json').read_text())['long']]
# Freeze both models'128 contexts before running any intervention in this check.
plans={}
for name in models:
 tok=AutoTokenizer.from_pretrained('/home/lmxxf/work/models/'+name,local_files_only=True);rng=np.random.default_rng(362);plans[name]=[]
 for i in range(128,256):
  ids=tok.encode(texts[i],add_special_tokens=False);k=int(rng.integers(5,min(len(ids)-1,129)));plans[name].append(dict(passage_index=i,endpoint=k,ids=ids))
(R/'confirmation_plan.json').write_text(json.dumps(dict(seed=362,reason='primary32pointGPT2nullandwideCIs; single new128-context check, same sites/dose/procedure; no result-based sample selection',plans=plans),indent=2))
nodes=[n for n in ast.parse((R/'run_reproduction.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['ent','baseline','suffix','plane_basis','sample_dirs']]
for name in models:
 torch.manual_seed(362);m=AutoModelForCausalLM.from_pretrained('/home/lmxxf/work/models/'+name,local_files_only=True,dtype=torch.float32,device_map='cuda',attn_implementation='sdpa').eval();m.requires_grad_(False)
 isgpt=name=='gpt2-xl';base=m.transformer if isgpt else m.gpt_neox;blocks=base.h if isgpt else base.layers;norm=base.ln_f if isgpt else base.final_layer_norm;head=m.get_output_embeddings();site=21 if isgpt else 11;L=len(blocks);env=dict(torch=torch,np=np,F=F,math=math,DynamicCache=DynamicCache,m=m,isgpt=isgpt,base=base,blocks=blocks,norm=norm,head=head,site=site,L=L);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<suffix>','exec'),env);raw=[]
 for t,p in enumerate(plans[name]):
  k=p['endpoint'];X,H,z0,cache=env['baseline'](p['ids'],k);D=X[1:k+2]-X[:k+1];P=env['plane_basis'](D[k-2:k]);scale=.2*float(D[k].norm());ap=F.normalize(D[k-2],dim=-1);b=F.normalize(D[k-1],dim=-1);c0=torch.acos(torch.dot(ap,b).clamp(-1,1))
  for family in ['full','planar2']:
   with torch.inference_mode():
    dirs=F.normalize(torch.randn(300,X.shape[-1],device='cuda'),dim=-1) if family=='full' else env['sample_dirs'](P,300,X.shape[-1]);delta=dirs*scale;v=F.normalize(D[k-1]+delta,dim=-1);dc=((torch.acos((v*ap).sum(-1).clamp(-1,1))-c0)/3).cpu().numpy();hs=[]
    for j in range(0,300,32):ee,zz=env['suffix'](X,cache,k,delta[j:j+32]);hs.extend(ee.tolist())
   raw.append(dict(sample=t,passage=p['passage_index'],endpoint=k,family=family,dc=dc.tolist(),dh=(np.array(hs)-H).tolist()))
  del X,cache,z0,zz;gc.collect();torch.cuda.empty_cache()
  if t%16==0:print(name,t,'/',128,flush=True)
 (R/name/'confirmation_raw.json').write_text(json.dumps(dict(site_zero_based=site,N_per_context=300,n_contexts=128,raw=raw),indent=2));print('CONFIRM_MODEL_DONE',name,flush=True)
 del m;torch.cuda.empty_cache()
(R/'confirmation_complete.json').write_text(json.dumps(dict(elapsed_seconds=time.time()-START,models=models),indent=2));print('CONFIRMATION_DONE',flush=True)
