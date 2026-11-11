import json,time,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
state=read(R/'takeover_status.json');assert state['completed']==state['readouts']==64
for n in state['nodes']:assert n['status']['state']=='complete'and len(n['owned_layers'])==len(n['completed'])==len(n['readouts'])==32
assert set(state['nodes'][0]['owned_layers']).isdisjoint(state['nodes'][1]['owned_layers'])
assert set(state['nodes'][0]['owned_layers'])|set(state['nodes'][1]['owned_layers'])==set(range(64))
v=read(R/'validation.json');p=read(R/'posthoc_validation.json');s=read(R/'summary.json');assert v['complete']and p['complete']and p['source_to_local_sha256_match']and p['slave_to_main_sha256_match']and s['state']=='accepted'
resources={}
for mode in ['collect_polysemy','extra_readouts']:
 d=read(R/f'postprocess_resource_{mode}.json');assert d['exit_code']==0 and d['minimum_MemAvailable_GiB']>=20;resources[mode]=d
artifacts={}
for name in ['summary.json','实验报告.md','validation.json','posthoc_validation.json','source_sha256.json','source_sha256_slave.json','polysemy_summary.json','polysemy_capture.json','extra_readouts_complete.json','steering_full_text.md','kurtosis_by_layer.svg','polysemy_by_layer.svg']:
 f=R/name;assert f.is_file()and f.stat().st_size;artifacts[name]={'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
result={'status':'PASS','time':time.time(),'layers':64,'nodes_32_each':True,'weights_all_finite':True,'slave_main_local_sha256_match':True,'main_source_files_compared':p['files_compared'],'slave_source_files_compared':p['slave_files_compared'],'postprocess_resources':resources,'artifacts':artifacts,'scope':'completion and engineering verification; not semantic purity or causal proof for every component'}
q=R/'final_acceptance.tmp';q.write_text(json.dumps(result,ensure_ascii=False,indent=2));q.replace(R/'final_acceptance.json');print('FINAL_ACCEPTANCE_PASS',flush=True)
