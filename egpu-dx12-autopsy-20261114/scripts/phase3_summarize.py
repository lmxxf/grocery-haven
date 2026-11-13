#!/usr/bin/env python3
import pathlib,re,statistics,json,math,csv,configparser
root=pathlib.Path(__file__).resolve().parents[1]/'build/phase3'
def quant(v,p):
 v=sorted(v);return v[math.ceil((len(v)-1)*p)] if v else None
def vals(line):return dict(re.findall(r'(\w+)=([^ ]+)',line))
def summarize(folder):
 text=(folder/'egpu_booster.window.log').read_text(encoding='utf-8-sig',errors='replace')
 snapshots=[vals(l) for l in text.splitlines() if l.startswith('snapshot ')]
 frames=[]
 for l in text.splitlines():
  if l.startswith('frame_samples_ms='):frames += [float(x) for x in l.split('=',1)[1].split(',') if x]
 dmon=[]
 for l in (folder/'dmon.txt').read_text(encoding='utf-8-sig').splitlines():
  if not l.strip() or l.lstrip().startswith('#'):continue
  try:
   v=[float(s) for s in l.split()];assert len(v)==11;dmon.append(v)
  except (ValueError,AssertionError):pass
 duration=sum(float(v['dt_s']) for v in snapshots)
 promotions=[vals(l) for l in text.splitlines() if l.startswith('promotion ')]
 ledger=[]
 for l in text.splitlines():
  if l.startswith('heap_ledger '):
   m=re.search(r'live_bytes_by_type=\[([^]]+)\]',l);ledger.append([int(x) for x in m[1].split(',')])
 sums={k:sum(int(v[k]) for v in snapshots) for k in ['presents','upload_bindings','upload_default_bytes','default_readback_bytes','submissions','commandlists','fence_events','fence_polls']}
 out={'label':folder.name,'window':json.loads((folder/'window.json').read_text(encoding='utf-8-sig')),'snapshot_count':len(snapshots),'telemetry_seconds':duration,'fps':sums['presents']/duration if duration else None,'frame_sample_count':len(frames),'frame_median_ms':statistics.median(frames) if frames else None,'frame_p99_ms':quant(frames,.99),'dmon_samples':len(dmon),'sm_mean_pct':statistics.mean(v[1] for v in dmon) if dmon else None,'rxpci_mean_MB_s':statistics.mean(v[9] for v in dmon) if dmon else None,'rxpci_p95_MB_s':quant([v[9] for v in dmon],.95),'txpci_mean_MB_s':statistics.mean(v[10] for v in dmon) if dmon else None,'txpci_p95_MB_s':quant([v[10] for v in dmon],.95),'interval_totals':sums,'final_promotion':promotions[-1] if promotions else {},'live_bytes_by_type_median':[statistics.median(v[i] for v in ledger) for i in range(5)] if ledger else [],'hook_failures_max':max((int(v['hook_failures']) for v in snapshots),default=None),'mclk_median_MHz':statistics.median(v[7] for v in dmon) if dmon else None,'pclk_median_MHz':statistics.median(v[8] for v in dmon) if dmon else None,'custom_l1_live_bytes_max':max([int(m) for m in re.findall(r'custom_l1_live_bytes=(\d+)',text)],default=0)}
 rows=list(csv.DictReader((folder/'gpu_query.csv').read_text(encoding='utf-8-sig').splitlines()))
 gen=set();width=set();temps=[];powers=[]
 for row in rows:
  fields={a.strip():b.strip() for a,b in row.items() if a and b}
  gen.add(fields.get('pcie.link.gen.current'));width.add(fields.get('pcie.link.width.current'))
  try:temps.append(float(fields['temperature.gpu']));powers.append(float(fields['power.draw [W]']))
  except (KeyError,ValueError):pass
 out.update(gpu_query_rows=len(rows),pcie_gen_seen=sorted(gen),pcie_width_seen=sorted(width),gpu_temp_range_C=[min(temps),max(temps)] if temps else [],power_mean_W=statistics.mean(powers) if powers else None)
 return out
if __name__=='__main__':
 results={}
 for folder in sorted(root.iterdir()):
  if folder.is_dir() and (folder/'egpu_booster.window.log').exists():results[folder.name]=summarize(folder)
 for name,mode,total,buf,heap in [('baseline_uncapped',0,256,64,128),('narrow20',1,20,8,16),('wide256',1,256,64,128)]:
  v=results[name];c=configparser.ConfigParser();c.read(root/name/'egpu_booster.ini')
  assert tuple(c.getint('booster',k) for k in ['mode','max_total_mb','max_buffer_mb','max_heap_mb'])==(mode,total,buf,heap),name
  assert v['dmon_samples']==60 and v['gpu_query_rows']>=55 and v['hook_failures_max']==0,name
  assert v['pcie_gen_seen']==['4'] and v['pcie_width_seen']==['4'],name
  assert v['frame_sample_count']>1000 and v['fps']>0,name
  assert int(v['final_promotion']['promoted_peak_bytes'])<=total*1048576,name
 print(json.dumps(results,indent=2))
