"""CPU-only, read-only takeover watcher. Alerts return to Codex's own pane.
Does not kill/restart models automatically; recovery is handled by the agent.
"""
import json,time,subprocess,os,sys
from pathlib import Path
R=Path(__file__).resolve().parent
remote='lmxxf@192.168.31.198';base='/home/lmxxf/work/jlens-qwen38-27b/'
def command(args):return subprocess.run(args,capture_output=True,text=True,timeout=25)
def probe(slave=False):
 cmd=['ssh','-o','ConnectTimeout=8',remote]
 if slave:cmd+=['ssh','-o','ConnectTimeout=8','169.254.30.81']
 z=command(cmd+['python3',base+'status_probe.py'])
 if z.returncode:raise RuntimeError(z.stderr.strip())
 return json.loads(z.stdout)
def read(p):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return {}
(R/'takeover_watch.pid').write_text(str(os.getpid()))
last_alert=None;failed=0
while True:
 try:
  a=probe();b=probe(True);failed=0
  phase=a['pipeline'].get('status','unknown');en=a.get('even',{}).get('completed',0);zh=b.get('odd',{}).get('completed',0)
  sync_pid=int((R/'sync.pid').read_text());sync_alive=Path(f'/proc/{sync_pid}').exists()
  info={'time':time.time(),'phase':phase,'completed':en+zh,'english':en,'chinese':zh,'available_GiB':[a['available_GiB'],b['available_GiB']],'model_alive':[a['model_alive'],b['model_alive']],'sync_alive':sync_alive,'master':a,'slave':b}
  tmp=R/'takeover_status.tmp';tmp.write_text(json.dumps(info,ensure_ascii=False));tmp.replace(R/'takeover_status.json')
  with open(R/'takeover_history.jsonl','a')as f:f.write(json.dumps(info,ensure_ascii=False)+'\n')
  problems=[]
  if not sync_alive and not (phase=='complete' and read(R/'results.json').get('complete') and (R/'Qwen3.8-27B_jacobian_lens.pt').exists() and (R/'lens_quality.svg').exists()):problems.append('local sync process exited')
  if phase=='failed':problems.append('remote pipeline failed')
  for tag,record,n in [('master',a,en),('slave',b,zh)]:
   if n<50 and phase in ['fitting_even','waiting_for_odd']:
    if not record['model_alive']:problems.append(tag+' model exited before 50')
    elif record.get(('even'if tag=='master'else'odd')+'_log_age',0)>180:problems.append(tag+' fitting log stalled >180s')
   if record['available_GiB']<22:problems.append(tag+' MemAvailable below22GiB')
  if problems and problems!=last_alert:
   command(['/home/lmxxf/.local/bin/herdr','agent','prompt','wM:p1','闇盯盘告警：'+'; '.join(problems)+'。请读取 grocery-haven/wechat-365-jlens-fit/takeover_status.json 并处理。'])
   last_alert=problems
  if not problems:last_alert=None
  result=read(R/'results.json')
  svg=all((R/x).exists()for x in ['convergence.svg','layer_structure.svg','lens_quality.svg'])
  lenses=all((R/f'lens_n{n}.pt').exists()for n in [1,2,4,10,20,50,100])
  done=phase=='complete' and result.get('complete') and svg and lenses and (R/'Qwen3.8-27B_jacobian_lens.pt').exists()
  print(json.dumps({k:info[k]for k in ['time','phase','completed','english','chinese','available_GiB','sync_alive']}|{'problems':problems,'ready_for_final_validation':bool(done)}),flush=True)
  if done:
   command(['/home/lmxxf/.local/bin/herdr','agent','prompt','wM:p1','闇接管盯盘：N=100远端流程和本地同步已到齐，请继续核验最终镜头SHA256/元数据/有限值、8阶段官方题集及8题64层Top-5、SVG和实验报告，更新最终验收文件后向Zero交付。当前状态见 grocery-haven/wechat-365-jlens-fit/takeover_status.json 。不要把本通知直接当验收通过。'])
   break
 except Exception as e:
  failed+=1;print(json.dumps({'error':repr(e),'consecutive_failures':failed,'time':time.time()}),flush=True)
  if failed==3:
   command(['/home/lmxxf/.local/bin/herdr','agent','prompt','wM:p1','闇盯盘连续三次探测失败：'+repr(e)+'。请检查SSH与日志。'])
 time.sleep(55)
