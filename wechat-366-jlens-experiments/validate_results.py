import json,math,hashlib,time,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent

def load(s):return json.loads((R/s).read_text())
e1=load('experiment1.json');assert len(e1['cases'])==9 and set(e1['stages'])=={'vanilla','n1','n100'}
positions=sum(len(c['token_ids'])for c in e1['cases'])
for stage,layers in e1['stages'].items():
 assert set(layers)==set(map(str,range(64)))
 for l,layer in layers.items():
  for c in e1['cases']:
   rows=layer[c['name']];assert len(rows)==len(c['token_ids'])
   for row in rows:
    assert len(row['top5'])==5 and all(math.isfinite(t['logit'])for t in row['top5'])
    assert all(1<=rank<=248320 for d in row['alias_ranks'].values()for rank in d.values())
    if c['conditional_rows']:assert all(1<=x['rank']<=100 and math.isfinite(x['joint_logprob'])for x in row['two_digit_00_99'].values())
assert e1['stages']['vanilla']['55']['tight'][-1]['top5'][0]['text']=='6'
assert e1['stages']['vanilla']['59']['tight'][-1]['top5'][0]['text']=='8'
e2=load('experiment2.json');assert len(e2['results'])==6
for q in e2['results']:
 assert len(q['conditions'])==18
 assert len([a for a in q['conditions']if 'generation'in a])==4
 for a in q['conditions']:
  assert math.isfinite(a['new_minus_old_sequence_logprob'])
  for v in a['targets'].values():assert math.isfinite(v['sequence_logprob']) and 1<=v['first_token_rank']<=248320
assert len(load('experiment3.json')['broadcast'])==3 and len(load('experiment3.json')['selectivity'])==2
e4=load('experiment4.json');assert len(e4['runs'])==14
assert len(load('experiment4_dosecheck.json')['runs'])==6
assert len(load('arithmetic_position_check.json')['runs'])==24
for f in R.glob('*.svg'):
 ET.parse(f);assert '#ffffff' in f.read_text(),f.name
assert len(list(R.glob('*.svg')))==5
import torch
torch.set_num_threads(4)
d=torch.load(R/'concept_directions.pt',map_location='cpu',weights_only=True)
for stage,layers in d.items():
 assert len(layers)==63
 for words in layers.values():assert all(v.shape==(5120,)and torch.isfinite(v).all()for v in words.values())
files=['experiment1.json','experiment2.json','experiment3.json','experiment4.json','experiment4_dosecheck.json','arithmetic_position_check.json']
out={'accepted':True,'time':time.time(),'experiment1_cases':9,'experiment1_positions':positions,'experiment1_stage_layer_position_records':positions*64*3,'readout_stages':['vanilla','n1','n100'],'layers':64,'swap_cases':6,'primary_swap_conditions':108,'introspection_runs':14,'all_reported_ranks_valid':True,'all_reported_scores_finite':True,'direction_shapes_and_finiteness_checked':True,'white_background_svg_count':5,'validation_device':'CPU only','raw_json_sha256':{f:hashlib.sha256((R/f).read_bytes()).hexdigest()for f in files}}
(R/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
