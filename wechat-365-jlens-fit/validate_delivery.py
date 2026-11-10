"""Final CPU-only acceptance. Run after pipeline, sync, plots and report finish."""
import json,hashlib,math,time,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent
import torch
torch.set_num_threads(4)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb')as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
r=json.loads((R/'results.json').read_text());assert r['complete']
e=json.loads((R/'evaluation_results.json').read_text());expected=['vanilla']+[f'n{n}'for n in [1,2,4,10,20,50,100]];assert list(e['stages'])==expected
for name,stage in e['stages'].items():
 reps=[x for x in stage['items']if x['group']=='representative'];assert len(reps)==8
 for row in stage['items']:
  assert set(row['layers'])==set(map(str,range(64)))
  for l,data in row['layers'].items():
   assert all(v is None or isinstance(v,int)and 1<=v<=248320 for v in data['ranks'].values())
   if row['group']=='representative':
    assert len(data['top5'])==5 and all(math.isfinite(t['logit'])for t in data['top5'])
 for row in stage['items']:
  for concept,best in row['min_ranks'].items():
   observed=[cell['ranks'][concept]for cell in row['layers'].values()if cell['ranks'][concept]is not None]
   assert best==(min(observed)if observed else None),(name,row['name'],concept)
 for group in ['multihop','multilingual']:
  rows=[row for row in stage['items']if row['group']==group]
  eligible=[[v for v in row['min_ranks'].values()if v is not None]for row in rows]
  usable=[v for v in eligible if v]
  m=stage['metrics'][group]
  assert len(rows)==(93 if group=='multihop'else 107)
  assert len(usable)==m['eligible_items']
  for k in [1,5,10]:
   independent=sum(sum(v<=k for v in row)/len(row)for row in usable)/len(usable)
   assert abs(independent-m[f'pass@{k}'])<1e-12,(name,group,k)
 for m in stage['metrics'].values():
  assert m['eligible_items']>0 and all(math.isfinite(m[f'pass@{k}'])and 0<=m[f'pass@{k}']<=1 for k in [1,5,10])
meta={}
for n in [1,2,4,10,20,50,100]:
 x=torch.load(R/f'lens_n{n}.pt',map_location='cpu',mmap=True,weights_only=True)
 assert x['n_prompts']==n and x['d_model']==5120 and x['source_layers']==list(range(63))
 assert all(v.shape==(5120,5120)and v.dtype==torch.float16 for v in x['J'].values())
 if n==100:
  for l,J in x['J'].items():
   for i in range(0,5120,64):assert torch.isfinite(J[i:i+64]).all(),(l,i)
 meta[n]={'n_prompts':n,'source_layers':63,'matrix_shape':[5120,5120],'dtype':'float16','bytes':(R/f'lens_n{n}.pt').stat().st_size}
 del x
for name in ['convergence.svg','layer_structure.svg','lens_quality.svg']:ET.parse(R/name)
assert 'n100' in (R/'lens_quality.svg').read_text()
assert '全部完成' in (R/'实验报告.md').read_text()
p=json.loads((R/'provenance.json').read_text());assert sha(R/'prompts_100.json')==p['hashes']['prompts_100.json']
for tag,parity in [('even',0),('odd',1)]:
 rows=[json.loads(line)for line in (R/f'convergence_{tag}.jsonl').read_text().splitlines()if line.strip()]
 assert len(rows)==50 and [x['local_N']for x in rows]==list(range(1,51)),tag
 assert [x['prompt_idx']for x in rows]==list(range(parity,100,2)),tag
assert sha(R/'loader_reference.py')==p['hashes']['loader_reference.py']
local_hash=sha(R/'lens_n100.pt')
canonical=R/'Qwen3.8-27B_jacobian_lens.pt'
assert canonical.resolve()==(R/'lens_n100.pt').resolve() or sha(canonical)==local_hash
z=subprocess.run(['ssh','-o','ConnectTimeout=10','lmxxf@192.168.31.198','sha256sum','/home/lmxxf/work/jlens-qwen38-27b/lens_n100.pt'],capture_output=True,text=True,check=True);remote_hash=z.stdout.split()[0];assert local_hash==remote_hash
out={'accepted':True,'time':time.time(),'checkpoints':meta,'evaluation_stages':expected,'all_pass_at_k_metrics_independently_recomputed':True,'all_concept_min_ranks_recomputed':True,'representative_cases_per_stage':8,'readout_layers':64,'all_n100_matrix_entries_finite':True,'n100_sha256_local':local_hash,'n100_sha256_remote':remote_hash,'validation_device':'CPU only; no local GPU','source_corpus_hash_matches':True,'loader_hash_matches':True,'all_100_training_prompt_indices_verified':True,'canonical_lens_matches_n100':True,'svg_xml_valid':True,'report_complete':True}
(R/'delivery_validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
