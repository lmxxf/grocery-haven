"""Prespecified layer-index sensitivity: use post-block20/10 instead of21/11."""
import ast,json,math,time,gc
from pathlib import Path
import torch,numpy as np
import torch.nn.functional as F
from transformers import AutoTokenizer,AutoModelForCausalLM
from transformers.cache_utils import DynamicCache
R=Path(__file__).resolve().parent;assert 'GB10' in torch.cuda.get_device_name();torch.set_num_threads(8);torch.set_float32_matmul_precision('highest');START=time.time()
nodes=[n for n in ast.parse((R/'run_reproduction.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['ent','baseline','suffix','plane_basis','sample_dirs']];texts=[x['text'] for x in json.loads((R/'corpus.json').read_text())['long']];allresults={}
for name in ['gpt2-xl','pythia-2.8b']:
 torch.manual_seed(361);tok=AutoTokenizer.from_pretrained('/home/lmxxf/work/models/'+name,local_files_only=True);m=AutoModelForCausalLM.from_pretrained('/home/lmxxf/work/models/'+name,local_files_only=True,dtype=torch.float32,device_map='cuda',attn_implementation='sdpa').eval();m.requires_grad_(False)
 isgpt=name=='gpt2-xl';base=m.transformer if isgpt else m.gpt_neox;blocks=base.h if isgpt else base.layers;norm=base.ln_f if isgpt else base.final_layer_norm;head=m.get_output_embeddings();site=20 if isgpt else 10;L=len(blocks)
 env=dict(torch=torch,np=np,F=F,math=math,DynamicCache=DynamicCache,m=m,isgpt=isgpt,base=base,blocks=blocks,norm=norm,head=head,site=site,L=L);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<suffix>','exec'),env);raw=[]
 for t in range(32):
  ids=tok.encode(texts[t],add_special_tokens=False);k=min(len(ids)-2,max(8,min(96,len(ids)//2)));X,H,z0,cache=env['baseline'](ids,k);D=X[1:k+2]-X[:k+1];P=env['plane_basis'](D[k-2:k]);U,S,Vh=torch.linalg.svd(D-D.mean(0),full_matrices=False);TQ=Vh[:2].T;scale=.2*float(D[k].norm());ap=F.normalize(D[k-2],dim=-1);b=F.normalize(D[k-1],dim=-1);c0=torch.acos(torch.dot(ap,b).clamp(-1,1))
  for family in ['full','trajectory2','planar2']:
   with torch.inference_mode():
    dirs=F.normalize(torch.randn(300,X.shape[-1],device='cuda'),dim=-1) if family=='full' else env['sample_dirs'](P if family=='planar2' else TQ,300,X.shape[-1]);delta=dirs*scale;v=F.normalize(D[k-1]+delta,dim=-1);dc=((torch.acos((v*ap).sum(-1).clamp(-1,1))-c0)/3).cpu().numpy();hs=[]
    for j in range(0,300,32):ee,zz=env['suffix'](X,cache,k,delta[j:j+32]);hs.extend(ee.tolist())
   raw.append(dict(sample=t,family=family,dc=dc.tolist(),dh=(np.array(hs)-H).tolist()))
  del X,cache,z0,zz;gc.collect();torch.cuda.empty_cache()
  if t%8==0:print(name,site,t,flush=True)
 (R/name/'layer_index_sensitivity_raw.json').write_text(json.dumps(dict(site_zero_based=site,raw=raw),indent=2))
 allresults[name]=dict(site_zero_based=site,mean_raw_r={f:float(np.mean([np.corrcoef(x['dc'],x['dh'])[0,1] for x in raw if x['family']==f])) for f in ['full','trajectory2','planar2']})
 del m;torch.cuda.empty_cache()
(R/'layer_index_sensitivity.json').write_text(json.dumps(dict(models=allresults,elapsed_seconds=time.time()-START),indent=2));print('SENSITIVITY_DONE',allresults,flush=True)
