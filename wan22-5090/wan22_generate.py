#!/usr/bin/env python3
"""Wan2.2 14B FP8, ComfyUI core-only HTTP CLI. Standard-library client; GPU runs on 5090."""
import argparse,json,time,uuid,secrets,sys,urllib.request,urllib.parse,urllib.error,hashlib,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))
NEGATIVE='overexposure, static image, blurry details, subtitles, watermark, worst quality, low quality, jpeg artifacts, deformed face, malformed limbs, extra fingers, fused fingers, cluttered background, three legs, walking backwards'
def request(server,path,data=None,headers=None,timeout=60):
 body=json.dumps(data).encode()if isinstance(data,dict)else data
 h={'Content-Type':'application/json'}if isinstance(data,dict)else{}
 h.update(headers or {})
 try:
  with OPENER.open(urllib.request.Request(server.rstrip('/')+path,data=body,headers=h),timeout=timeout)as r:
   raw=r.read();return json.loads(raw)if raw else{}
 except urllib.error.HTTPError as e:raise RuntimeError(f'HTTP {e.code}: {e.read().decode(errors="replace")}')from e
def upload(server,path):
 p=Path(path);boundary='wan22'+uuid.uuid4().hex;body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{p.name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+p.read_bytes()+f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\nfalse\r\n--{boundary}--\r\n'.encode()
 d=request(server,'/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary});return (d.get('subfolder','')+'/'if d.get('subfolder')else'')+d['name']
def graph(args,image_name=None):
 kind='i2v'if image_name else't2v';split=args.split_step if args.split_step is not None else args.steps//2
 if not 0<split<args.steps:raise ValueError('split-step must be between 0 and steps')
 def node(t,**i):return {'class_type':t,'inputs':i}
 g={
 '1':node('UNETLoader',unet_name=f'wan2.2_{kind}_high_noise_14B_fp8_scaled.safetensors',weight_dtype='default'),
 '2':node('UNETLoader',unet_name=f'wan2.2_{kind}_low_noise_14B_fp8_scaled.safetensors',weight_dtype='default'),
 '3':node('CLIPLoader',clip_name='umt5_xxl_fp8_e4m3fn_scaled.safetensors',type='wan',device='default'),
 '4':node('VAELoader',vae_name='wan_2.1_vae.safetensors'),
 '5':node('CLIPTextEncode',clip=['3',0],text=args.prompt),
 '6':node('CLIPTextEncode',clip=['3',0],text=args.negative),
 '8':node('ModelSamplingSD3',model=['1',0],shift=5.),
 '9':node('ModelSamplingSD3',model=['2',0],shift=5.)}
 if image_name:
  g['15']=node('LoadImage',image=image_name)
  g['7']=node('WanImageToVideo',positive=['5',0],negative=['6',0],vae=['4',0],width=args.width,height=args.height,length=args.frames,batch_size=1,start_image=['15',0]);pos=['7',0];neg=['7',1];latent=['7',2]
 else:
  g['7']=node('EmptyHunyuanLatentVideo',width=args.width,height=args.height,length=args.frames,batch_size=1);pos=['5',0];neg=['6',0];latent=['7',0]
 common={'noise_seed':args.seed,'steps':args.steps,'cfg':args.cfg,'sampler_name':'euler','scheduler':'simple','positive':pos,'negative':neg}
 g['10']=node('KSamplerAdvanced',**common,model=['8',0],add_noise='enable',start_at_step=0,end_at_step=split,return_with_leftover_noise='enable',latent_image=latent)
 g['11']=node('KSamplerAdvanced',**common,model=['9',0],add_noise='disable',start_at_step=split,end_at_step=args.steps,return_with_leftover_noise='disable',latent_image=['10',0])
 g['12']=node('VAEDecode',samples=['11',0],vae=['4',0]);g['13']=node('CreateVideo',images=['12',0],fps=float(args.fps))
 g['14']=node('SaveVideo',video=['13',0],filename_prefix=args.prefix,format='mp4')
 return g

def files_in(x):
 if isinstance(x,dict):
  if isinstance(x.get('filename'),str)and x['filename'].lower().endswith(('.mp4','.webm','.mov')):yield x
  for v in x.values():yield from files_in(v)
 elif isinstance(x,list):
  for v in x:yield from files_in(v)
def save(path,x):
 q=path.with_suffix('.tmp');q.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False));q.replace(path)
def inspect_video(path,frames=True):
 ffprobe=shutil.which('ffprobe');ffmpeg=shutil.which('ffmpeg');result={}
 if ffprobe:
  p=subprocess.run([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,text=True,check=True);result['ffprobe']=json.loads(p.stdout)
 if frames and ffmpeg:
  dest=path.with_suffix('');dest.mkdir(exist_ok=True)
  subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(path),'-vf','select=eq(n\\,0)+eq(n\\,40)+eq(n\\,80)','-vsync','0',str(dest/'frame_%02d.png')],check=True)
  result['keyframes']=[str(p)for p in sorted(dest.glob('*.png'))]
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--server',default='http://192.168.31.50:8188');ap.add_argument('--prompt');ap.add_argument('--negative',default=NEGATIVE);ap.add_argument('--image');ap.add_argument('--seed',type=int);ap.add_argument('--width',type=int,default=832);ap.add_argument('--height',type=int,default=480);ap.add_argument('--frames',type=int,default=81);ap.add_argument('--fps',type=float,default=16);ap.add_argument('--steps',type=int,default=20);ap.add_argument('--split-step',type=int);ap.add_argument('--cfg',type=float,default=3.5);ap.add_argument('--output-dir',type=Path,default=ROOT/'outputs');ap.add_argument('--prefix');ap.add_argument('--timeout',type=float,default=7200);ap.add_argument('--poll',type=float,default=2);ap.add_argument('--no-keyframes',action='store_true');ap.add_argument('--unload-after',action='store_true',help='release GPU models after download; server stays available');ap.add_argument('--workflow',type=Path);ap.add_argument('--resume',help='existing ComfyUI prompt_id');ap.add_argument('--dry-run',action='store_true');args=ap.parse_args()
 if not args.prompt and not args.resume:ap.error('--prompt is required unless --resume is supplied')
 if args.width%16 or args.height%16 or(args.frames-1)%4:ap.error('width/height must be multiples of16; frames must be4n+1')
 args.seed=args.seed if args.seed is not None else secrets.randbits(32);args.prefix=args.prefix or f'Wan22/{"i2v"if args.image else"t2v"}_{args.seed}'
 args.output_dir.mkdir(parents=True,exist_ok=True);run=uuid.uuid4().hex[:8];statepath=args.output_dir/f'job_{run}.json';start=time.time();state={'state':'preparing','server':args.server,'started':start,'parameters':{k:str(v)if isinstance(v,Path)else v for k,v in vars(args).items()},'files':[]};save(statepath,state)
 try:
  if args.resume:pid=args.resume
  else:
   image_name=upload(args.server,args.image)if args.image and not args.dry_run else(Path(args.image).name if args.image else None)
   g=json.loads(args.workflow.read_text())if args.workflow else graph(args,image_name)
   if args.workflow:
    required={'5','6','7','10','11','13','14'}
    if not required.issubset(g):raise ValueError('--workflow must use the node IDs of the supplied Wan22 API templates')
    g['5']['inputs']['text']=args.prompt;g['6']['inputs']['text']=args.negative
    g['7']['inputs'].update(width=args.width,height=args.height,length=args.frames,batch_size=1)
    split=args.split_step if args.split_step is not None else args.steps//2
    for n in ['10','11']:g[n]['inputs'].update(noise_seed=args.seed,steps=args.steps,cfg=args.cfg)
    g['10']['inputs'].update(start_at_step=0,end_at_step=split);g['11']['inputs'].update(start_at_step=split,end_at_step=args.steps)
    g['13']['inputs']['fps']=float(args.fps);g['14']['inputs']['filename_prefix']=args.prefix
    if image_name:
     if '15'not in g:raise ValueError('--image requires the I2V API template')
     g['15']['inputs']['image']=image_name
   state['workflow']=g
   if args.dry_run:
    state.update(state='dry_run');save(statepath,state);print(json.dumps(g,indent=2));return
   state['system_stats_at_submit']=request(args.server,'/system_stats')
   response=request(args.server,'/prompt',{'prompt':g,'client_id':run});pid=response['prompt_id'];state['submission']=response
  state.update(prompt_id=pid,state='queued');save(statepath,state);print(f'prompt_id={pid} job={statepath}',flush=True);last=-1
  while True:
   if time.time()-start>args.timeout:raise TimeoutError(f'Wait timeout; server job remains queued/running. Resume with --resume {pid}')
   h=request(args.server,'/history/'+urllib.parse.quote(pid))
   if pid in h:
    history=h[pid];state['history']=history
    if history.get('status',{}).get('status_str')=='error':raise RuntimeError(json.dumps(history['status'],ensure_ascii=False))
    if history.get('status',{}).get('completed',bool(history.get('outputs'))):break
   elapsed=int(time.time()-start)
   if elapsed//15!=last:last=elapsed//15;print(f'waiting {elapsed}s',flush=True)
   time.sleep(args.poll)
  state['wait_seconds_until_history_complete']=time.time()-start
  messages=history.get('status',{}).get('messages',[]);times={m[0]:m[1].get('timestamp')for m in messages if isinstance(m,list)and len(m)==2 and isinstance(m[1],dict)}
  if times.get('execution_start')and times.get('execution_success'):state['server_execution_seconds']=(times['execution_success']-times['execution_start'])/1000
  dedup=set()
  for f in files_in(history.get('outputs',{})):
   key=(f['filename'],f.get('subfolder',''),f.get('type','output'))
   if key in dedup:continue
   dedup.add(key);dest=args.output_dir/(run+'_'+Path(f['filename']).name);params=urllib.parse.urlencode({'filename':key[0],'subfolder':key[1],'type':key[2]})
   with OPENER.open(args.server.rstrip('/')+'/view?'+params,timeout=300)as src,dest.open('wb')as out:shutil.copyfileobj(src,out)
   item={'path':str(dest),'server_file':f,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()};item.update(inspect_video(dest,not args.no_keyframes));state['files'].append(item);print('downloaded',dest,flush=True)
  if not state['files']:raise RuntimeError('History completed without video artifact')
  if args.unload_after:request(args.server,'/free',{'unload_models':True,'free_memory':True})
  state.update(state='complete',finished=time.time(),wall_seconds=time.time()-start);save(statepath,state);print(f'complete {state["wall_seconds"]:.2f}s: {statepath}',flush=True)
 except BaseException as e:
  state.update(state='failed',error=repr(e),elapsed_seconds=time.time()-start);save(statepath,state);raise
if __name__=='__main__':main()
