"""Recompute statistics from saved ICA coordinates, grouping EN-C by surname set."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT));import run_exp1a as e
probes=e.load(ROOT/'probes.json');_,pairs,groups=e.construct();e.save('pairs.json',pairs);e.save('groups.json',groups)
z=np.load(ROOT/'z_last.npy',mmap_mode='r');zm=np.load(ROOT/'z_mean.npy',mmap_mode='r');rs=[]
for l in range(64):
 kurt=e.load(e.ROOT/f'L{l:02d}/statistics.json')['test']['excess_kurtosis'];rs.append(e.analyze_layer(z[l],zm[l],pairs,groups,kurt,l))
e.save('results_all_layers.json',rs);rd=e.load(ROOT/'representative_readouts.json');reps=e.load(ROOT/'representatives.json')+e.load(ROOT/'supplemental_representatives.json');meta=e.load(ROOT/'run_metadata.json');meta.update(failed_startups=1,full_model_loads_including_failed_startup=2,successful_forward_model_loads=1,supplemental_readout='norm and unembedding weights only; zero probe forwards');e.save('run_metadata.json',meta)
e.report(rs,reps,rd,probes,pairs,groups,meta)
p=ROOT/'report_exp1a.md';text=p.read_text().replace('模型只加载一次。','正式运行完整模型加载一次（另有首条前向前的缓存权限失败记录，见文末）。').replace('英文与空间对照从未参与选层。','英文与空间对照未参与前三个代表层的选择。另外补读 L37（EN-A全对）与 L42（EN-C全对）两层解释曲线差异；这两层是看完英文结果后追加的描述性样本。').replace('测量的是姓氏与关系绑定带来的响应。','测量的是姓氏与关系绑定带来的响应；EN-C按5套姓氏聚合置换，每套3类亲属属于重复测量。')
p.write_text(text)
import enrich_exp1a;enrich_exp1a.run()
