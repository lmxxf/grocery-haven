"""Read two transfer examples using only outside norm/unembedding weights; no forward/model reload."""
import os,sys,gc
from pathlib import Path
ROOT=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT));sys.path.insert(0,str(ROOT))
import run_exp1a as e
import numpy as np
from safetensors.torch import load_file
from common import readout_model
results=e.load(OUT/'results_all_layers.json');old=e.load(OUT/'representative_readouts.json');original=e.load(OUT/'representatives.json')
extras=[]
for l in [37,42]:
 v=results[l]['selectors']['S2']['delta'][0];extras.append(dict(layer=l,selector='S2',method='delta',axis=v['axis'],sign=v['sign']))
model,tok=readout_model();new=e.readout(model,tok,extras);del model;gc.collect()
manifest=e.load(ROOT/'hf_clean_upload/icalens.json')
for rd in new:
 l=rd['layer'];c=rd['axis'];asset=load_file(str(ROOT/'hf_clean_upload'/manifest['layers'][str(l)]['file']));C=asset['reading_matrix'].numpy();M=asset['writing_matrix'].numpy();rd['axis_geometry']=[]
 for g in ['physical','social','EN_A','EN_C']:
  for method in ['delta','t']:
   c2=results[l]['independent_top1'][g][method]['axis'];cos=lambda a,b:float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)))
   rd['axis_geometry'].append(dict(group=g,method=method,axis=c2,reading_cosine=cos(C[c],C[c2]),writing_cosine=cos(M[:,c],M[:,c2])))
 rd['selection_note']='Supplemental descriptive transfer inspection after all curves: L37 EN-A 25/25; L42 EN-C 15/15; not used for unbiased success-rate estimation.'
allread=old+new;e.save('representative_readouts.json',allread);e.save('supplemental_representatives.json',extras)
z=np.load(OUT/'z_last.npy',mmap_mode='r');zm=np.load(OUT/'z_mean.npy',mmap_mode='r');probes=e.load(OUT/'probes.json');pairs=e.load(OUT/'pairs.json');groups=e.load(OUT/'groups.json');meta=e.load(OUT/'run_metadata.json')
e.save('representative_raw_scores.json',[dict(id=p['id'],text=p['text'],values=[dict(layer=rd['layer'],axis=rd['axis'],z_last=float(z[rd['layer'],p['id'],rd['axis']]),z_mean=float(zm[rd['layer'],p['id'],rd['axis']])) for rd in allread]) for p in probes])
e.report(results,original+extras,allread,probes,pairs,groups,meta)
p=OUT/'report_exp1a.md';text=p.read_text().replace('模型只加载一次。','正式运行完整模型加载一次（另有首条前向前的缓存权限失败记录，见文末）。').replace('英文与空间对照从未参与选层。','英文与空间对照未参与前三个代表层的选择。另外补读 L37（EN-A全对）与 L42（EN-C全对）两层解释曲线差异；这两层是看完英文结果后追加的描述性样本。')
p.write_text(text)
