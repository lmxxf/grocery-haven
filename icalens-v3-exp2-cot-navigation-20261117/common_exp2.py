import os,json,time,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
V3=Path('/home/lmxxf/work/ica-lens-qwen38-27b-v3');H=V3/'experiments/exp2_cot_navigation';PYTHON='/home/lmxxf/work/interp-curvature-exp/venv/bin/python'
os.environ['TRITON_CACHE_DIR']=str(V3/'triton_cache');os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
def read(p):return json.loads(Path(p).read_text())
def save(name,obj,heavy=False):
 text=json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False);p=(H if heavy or len(text.encode())>10_000_000 else R)/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p

def append(title,body):
 with (R/'DevHistory.md').open('a') as f:f.write('\n## '+time.strftime('%Y-%m-%d %H:%M:%S %z')+'｜'+title+'\n\n'+body.strip()+'\n')
 print('HISTORY',title,flush=True)
def hashfile(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
