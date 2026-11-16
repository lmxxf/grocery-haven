"""Add one same-layer semantic check using only saved J plus norm/unembedding weights."""
import sys,json,gc
from pathlib import Path
R=Path(__file__).resolve().parent;V3=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3');H=V3/'experiments/exp1b_archaic_nucai';sys.path.insert(0,str(R));sys.path.insert(0,str(V3))
import torch,numpy as np
import analysis_exp1b as a
from common import readout_model
rs=a.read(H/'all_layers_full.json');reps=a.read(R/'representatives.json');rd=a.read(R/'representative_readouts.json');v=rs[45]['references']['R1_Humiliation']['delta'];new=dict(layer=45,axis=v['axis'],sign=v['sign'],name='R1_Humiliation',method='delta',selection_note='Additional same-layer check with L45 court axis; descriptive after inspecting full curves')
if not any(x['layer']==45 and x['name']=='R1_Humiliation' for x in reps):
 torch.set_num_threads(8);torch.set_float32_matmul_precision('highest');model,tok=readout_model();extra=a.readouts(model,tok,[new],a.read(V3/'hf_clean_upload/icalens.json'));del model;gc.collect();reps.append(new);rd.extend(extra);a.save('representatives.json',reps);a.save('representative_readouts.json',rd)
probes=a.read(R/'probes.json');z=np.load(H/'z_last.npy',mmap_mode='r');zm=np.load(H/'z_mean.npy',mmap_mode='r')
a.save('representative_raw_scores.json',[dict(id=p['id'],text=p['text'],target=p['target'],readings=[dict(name=x['name'],layer=x['layer'],axis=x['axis'],z_last=float(z[x['layer'],p['id'],x['axis']]),z_mean=float(zm[x['layer'],p['id'],x['axis']])) for x in reps]) for p in probes])
