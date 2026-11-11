import json,time,hashlib,subprocess,importlib.metadata as md
from pathlib import Path
R=Path(r'C:\AI\Wan22-ComfyUI');app=R/'ComfyUI_windows_portable/ComfyUI'
versions={}
for name in ['torch','torchvision','torchaudio','triton-windows','sageattention','comfyui-frontend-package','comfyui-workflow-templates','av']:
 try:versions[name]=md.version(name)
 except md.PackageNotFoundError:versions[name]=None
manifest=json.loads((R/'scripts/model_manifest.json').read_text(encoding='utf-8-sig'));files=[]
for f in manifest:
 p=app/'models'/Path(f['path']).relative_to('split_files');h=hashlib.sha256();start=time.perf_counter()
 with p.open('rb')as data:
  for b in iter(lambda:data.read(16*1024**2),b''):h.update(b)
 assert p.stat().st_size==f['size']and h.hexdigest()==f['sha256'],str(p)
 files.append({**f,'installed_path':str(p),'actual_sha256':h.hexdigest(),'verified':True,'hash_seconds':time.perf_counter()-start});print('HASH_VERIFIED',p.name,flush=True)
ffmpeg=next((R/'tools/ffmpeg').rglob('ffmpeg.exe'));ffmpeg_version=subprocess.check_output([str(ffmpeg),'-version'],text=True).splitlines()[0]
try:
 import pygit2
 commit=str(pygit2.Repository(str(app)).head.target)
except Exception:commit=None
result={'time':time.time(),'windows_root':str(R),'comfyui_dir':str(app),'comfyui_commit':commit,'versions':versions,'models':files,'ffmpeg_path':str(ffmpeg),'ffmpeg_version':ffmpeg_version,'gpu_smoke':json.loads((R/'logs/gpu_smoke.json').read_text()),'attention_benchmark':json.loads((R/'logs/attention_benchmark.json').read_text()),'server_config':json.loads((R/'server_config.json').read_text(encoding='utf-8-sig')),'startup_task':'Wan22-ComfyUI','startup_context':'SYSTEM, AtStartup; manually started and verified, no reboot performed','proxy_requirement':'none for inference, temporary Spark relay stopped'}
(R/'logs/installation_inventory.json').write_text(json.dumps(result,indent=2));print('INVENTORY_COMPLETE')
