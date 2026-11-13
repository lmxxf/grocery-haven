#!/usr/bin/env python3
import pathlib,re,json,statistics,datetime,csv,math,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]/'build/phase4'
def fields(line):return dict(re.findall(r'(\w+)=([^\s]+)',line))
def utc(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def quant(v,p):
 v=sorted(v);return v[math.ceil((len(v)-1)*p)] if v else None
def analyze(p):
 text=(p/'egpu_booster.window.log').read_text(encoding='utf-8-sig',errors='replace');groups=[];g=None
 for line in text.splitlines():
  if line.startswith('profile_window '):
   if g and 'snapshot' in g:groups.append(g)
   g={'window':fields(line),'api':{},'threads':[],'copies':[],'frames':[]}
  elif g:
   if line.startswith('cpu_api '):v=fields(line);g['api'][v['name']]=v
   elif line.startswith('cpu_thread '):g['threads'].append(fields(line))
   elif line.startswith('copy_detail '):g['copies'].append(fields(line))
   elif line.startswith('frame_samples_ms='):g['frames']=[float(x) for x in line.split('=',1)[1].split(',') if x]
   elif line.startswith('snapshot '):g['snapshot']=fields(line)
   elif line.startswith('wait_detail '):g['wait']=fields(line)
 if g and 'snapshot' in g:groups.append(g)
 queries=[]
 for row in csv.DictReader((p/'gpu_query.csv').read_text(encoding='utf-8-sig',errors='replace').splitlines()):
  v={k.strip():s.strip() for k,s in row.items() if k and s}
  try:t=datetime.datetime.strptime(v['timestamp'],'%Y/%m/%d %H:%M:%S.%f').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8))).astimezone(datetime.timezone.utc);queries.append((t,float(v['utilization.gpu [%]'].split()[0])))
  except (ValueError,KeyError):continue
 dmon=[]
 for line in (p/'dmon.txt').read_text().splitlines():
  try:v=[float(x) for x in line.split()]
  except ValueError:continue
  if len(v)==11:dmon.append(v)
 for g in groups:
  end=utc(g['window']['utc']);begin=end-datetime.timedelta(seconds=float(g['window']['dt_s']));util=[v for t,v in queries if begin<t<=end];g['gpu_query_mean']=statistics.mean(util) if util else None
  g['fps']=float(g['snapshot']['fps']);g['target']=bool(g['gpu_query_mean'] is not None and g['gpu_query_mean']<=60 and 30<=g['fps']<=50)
 usable=groups
 if p.name.startswith('wukong'):usable=[g for g in groups if 5<g['fps']<150 and float(g['snapshot']['frame_median_ms'])>=7]
 n=sum(int(g['window']['presents']) for g in usable);secs=sum(float(g['window']['dt_s']) for g in usable);frames=sum((g['frames'] for g in usable),[])
 apis={};threads={};copies={}
 for g in usable:
  for name,v in g['api'].items():
   a=apis.setdefault(name,dict(calls=0,total_us=0,long_calls=0,max_us=0));a['calls']+=int(v['calls']);a['total_us']+=float(v['total_us']);a['long_calls']+=int(v['long_gt_500us']);a['max_us']=max(a['max_us'],float(v['max_us']))
  for v in g['threads']:
   key=v['tid']+'|'+v['thread'];a=threads.setdefault(key,{});a[v['api']]=a.get(v['api'],0)+float(v['total_us'])
  for v in g['copies']:
   key=v['direction']+'_'+v['kind'];a=copies.setdefault(key,dict(calls=0,bytes=0,unknown=0));a['calls']+=int(v['calls']);a['bytes']+=int(v['bytes']);a['unknown']+=int(v['unknown_size_calls'])
 for a in apis.values():a['ms_per_present']=a['total_us']/1000/n if n else None
 for a in threads.values():
  for k in a:a[k]=a[k]/1000/n if n else None
 for a in copies.values():a['MB_s']=a['bytes']/1e6/secs if secs else None;a['bytes_per_present']=a['bytes']/n if n else None
 targets=[dict(utc=g['window']['utc'],fps=g['fps'],gpu=g['gpu_query_mean'],cpu={k:float(v['per_present_ms']) for k,v in g['api'].items()}) for g in usable if g['target']]
 out=dict(label=p.name,windows=len(usable),presents=n,seconds=secs,fps=n/secs if secs else None,frame_median_ms=statistics.median(frames) if frames else None,frame_p99_ms=quant(frames,.99),dmon_n=len(dmon),sm_mean=statistics.mean(v[1] for v in dmon) if dmon else None,sm_median=statistics.median(v[1] for v in dmon) if dmon else None,rx_MB_s=statistics.mean(v[9] for v in dmon) if dmon else None,tx_MB_s=statistics.mean(v[10] for v in dmon) if dmon else None,api=apis,threads=threads,copies=copies,target_windows=targets,hook_failures=max((int(g['snapshot']['hook_failures']) for g in usable),default=None))
 bins=[0]*4;evictions=overflow=0;mixed=0.0
 for line in text.splitlines():
  if line.startswith('wait_detail '):
   match=re.search(r'readback_size_bins=\[([^]]+)\]',line)
   if match:
    for i,v in enumerate(match[1].split(',')):bins[i]+=int(v)
   evictions+=int(re.search(r'event_ring_evictions=(\d+)',line)[1]);overflow+=int(re.search(r'thread_slot_overflow=(\d+)',line)[1]);mixed+=float(re.search(r'mixed_fence_us=([\d.]+)',line)[1])
 out.update(readback_size_bins_all_captured_windows=bins,event_ring_evictions=evictions,thread_slot_overflow=overflow,mixed_fence_wait_us=mixed)
 queryRows=list(csv.DictReader((p/'gpu_query.csv').read_text(encoding='utf-8-sig').splitlines()));queryKeys={k.strip():k for k in queryRows[0]}
 out['pcie_gen_seen']=sorted({v[queryKeys['pcie.link.gen.current']].strip() for v in queryRows});out['pcie_width_seen']=sorted({v[queryKeys['pcie.link.width.current']].strip() for v in queryRows});out['gpu_query_rows']=len(queryRows)
 start=p/'thread_cpu_start.json';end=p/'thread_cpu_end.json'
 if start.exists() and end.exists():
  a=json.loads(start.read_text(encoding='utf-8-sig'));b=json.loads(end.read_text(encoding='utf-8-sig'));a={v['tid']:v for v in (a if isinstance(a,list) else [a])};window=json.loads((p/'window.json').read_text(encoding='utf-8-sig'));wall=(utc(window['endUtc'])-utc(window['startUtc'])).total_seconds();active=[]
  for v in b if isinstance(b,list) else [b]:
   if v['tid'] in a:delta=(v['cpu100ns']-a[v['tid']]['cpu100ns'])/1e7
   elif utc(v['startUtc'])>=utc(window['startUtc']):delta=v['cpu100ns']/1e7
   else:continue
   active.append(dict(tid=v['tid'],name=v.get('name'),cpu_seconds=delta,one_core_pct=100*delta/wall))
  labels={int(k.split('|',1)[0]):k.split('|',1)[1] for k in threads}
  for v in active:
   if not v.get('name'):v['name']=labels.get(v['tid'],'unknown')
  out['thread_active']=sorted(active,key=lambda v:v['cpu_seconds'],reverse=True)
 (p/'analysis.json').write_text(json.dumps(out,indent=2));return out
if __name__=='__main__':
 cases=[ROOT/n for n in sys.argv[1:]] if len(sys.argv)>1 else [p for p in ROOT.iterdir() if p.is_dir() and (p/'window.json').exists() and (p/'egpu_booster.window.log').exists()]
 for p in cases:
  v=analyze(p);print(v['label'],json.dumps({k:v[k] for k in ['fps','frame_median_ms','frame_p99_ms','sm_mean','rx_MB_s','tx_MB_s','hook_failures']},ensure_ascii=False));print('targets',len(v['target_windows']));print('API ms/present',{k:round(a['ms_per_present'],3) for k,a in v['api'].items()})
