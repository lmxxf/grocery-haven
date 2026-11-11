#!/usr/bin/env python3
import argparse,subprocess,time,json,sys,csv,hashlib,urllib.request
from pathlib import Path
from PIL import Image
import numpy as np
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));from remote_ps import run as winps
from wan22_generate import request
PROMPT='A small orange fox walks slowly through a sunlit meadow. Colorful wildflowers sway gently in the breeze. Smooth cinematic tracking shot, realistic fur detail, warm morning light, natural coherent movement, continuous shot, no cuts.'
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--backend',choices=['sdpa','sage'],required=True);p.add_argument('--image');p.add_argument('--prompt',default=PROMPT);p.add_argument('--seed',type=int,default=20261111);a=p.parse_args();dest=R/'outputs'/a.name;dest.mkdir(parents=True,exist_ok=True);server='http://192.168.31.50:8188'
control=winps("& 'C:\\AI\\Wan22-ComfyUI\\scripts\\start_service.ps1' -Backend "+a.backend,capture_output=True,text=True);assert control.returncode==0,control.stderr
for i in range(180):
 try:
  stats=request(server,'/system_stats',timeout=3)
  if (a.backend=='sage')!=('--use-sage-attention'in stats['system'].get('argv',[])):raise RuntimeError('Backend does not match requested mode')
  break
 except Exception as e:
  if i==179:raise
  time.sleep(1)
monitor=winps("& 'C:\\AI\\Wan22-ComfyUI\\scripts\\monitor_start.ps1' -Name '"+a.name+"'",capture_output=True,text=True);assert monitor.returncode==0,monitor.stderr
cmd=[sys.executable,str(R/'wan22_generate.py'),'--prompt',a.prompt,'--seed',str(a.seed),'--prefix','acceptance/'+a.name,'--output-dir',str(dest),'--timeout','7200']
if a.image:cmd+=['--image',a.image]
try:
 with(R/'logs'/f'{a.name}_client.log').open('w')as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=log);print('GENERATION_STARTED',a.name,'client_pid',proc.pid,flush=True);code=proc.wait()
 if code:raise RuntimeError(f'Client failed code={code}; see logs/{a.name}_client.log')
finally:winps("Stop-ScheduledTask -TaskName 'Wan22-GPU-Monitor'",capture_output=True,text=True)
subprocess.run([sys.executable,str(R/'download_file.py'),f'C:/AI/Wan22-ComfyUI/logs/gpu_{a.name}.csv',str(R/'logs'/f'gpu_{a.name}.csv')],check=True)
with(R/'logs'/f'gpu_{a.name}.csv').open(encoding='utf-8-sig')as f:rows=list(csv.reader(f))
memory=[]
for row in rows:
 try:memory.append(float(row[1]))
 except (ValueError,IndexError):pass
assert memory
jobs=list(dest.glob('job_*.json'));job=max(jobs,key=lambda p:p.stat().st_mtime);data=json.loads(job.read_text());assert data['state']=='complete';file=data['files'][0];stream=next(x for x in file['ffprobe']['streams']if x['codec_type']=='video');assert(stream['codec_name'],stream['width'],stream['height'],int(stream['nb_frames']))==('h264',832,480,81),stream
frames=[];arrays=[]
for path in file['keyframes']:
 arr=np.array(Image.open(path).convert('RGB'),dtype=np.float32);luma=arr@np.array([.2126,.7152,.0722]);record={'path':path,'mean_luma':float(luma.mean()),'spatial_std_luma':float(luma.std()),'rgb_spatial_std':arr.reshape(-1,3).std(axis=0).tolist()};assert record['mean_luma']>2 and record['spatial_std_luma']>3,record;frames.append(record);arrays.append(arr)
assert len(frames)==3
result={'name':a.name,'backend':a.backend,'job_file':str(job),'prompt_id':data['prompt_id'],'server_execution_seconds':data.get('server_execution_seconds'),'client_wall_seconds':data['wall_seconds'],'wait_seconds_until_history_complete':data['wait_seconds_until_history_complete'],'video':file['path'],'bytes':file['bytes'],'video_sha256':file['sha256'],'codec':stream['codec_name'],'width':stream['width'],'height':stream['height'],'frames':int(stream['nb_frames']),'playback_fps':stream['r_frame_rate'],'duration':file['ffprobe']['format'].get('duration'),'gpu_total_peak_MiB_sampled_500ms':max(memory),'gpu_total_min_MiB':min(memory),'gpu_samples':len(memory),'keyframe_checks':frames,'keyframe_temporal_mean_absolute_difference':[float(np.abs(arrays[i]-arrays[i-1]).mean())for i in range(1,len(arrays))],'automatic_basic_video_checks':'pass','manual_visual_review':'pending','note':'end-to-end includes loading; OS file cache and concurrent downloads differ across runs; GPU peak includes desktop and CUDA context'}
(R/'logs'/f'{a.name}_result.json').write_text(json.dumps(result,indent=2));print('CASE_COMPLETE',json.dumps(result),flush=True)
