from pathlib import Path
import os,json,time,requests
os.environ['HF_HUB_DISABLE_XET']='1'
from huggingface_hub import snapshot_download
R=Path(__file__).resolve().parent
for repo,rev in [('openai-community/gpt2-xl','15ea56dee5df4983c59b2538573817e1667135e2'),('EleutherAI/pythia-2.8b','2a259cdd96a4beb1cdf467512e3904197345f6a9')]:
 dest=Path('/home/lmxxf/work/models')/repo.split('/')[-1]
 print('START',repo,time.ctime(),flush=True)
 snapshot_download(repo_id=repo,revision=rev,local_dir=dest,allow_patterns=['*.json','*.safetensors','merges.txt','vocab.json'],max_workers=4)
 print('DONE',repo,time.ctime(),flush=True)
