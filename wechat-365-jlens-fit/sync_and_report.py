"""CPU-only local completion watcher; portable artifacts stay in grocery-haven."""
import os,time,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
remote='lmxxf@192.168.31.198';base='/home/lmxxf/work/jlens-qwen38-27b/'
(R/'sync.pid').write_text(str(os.getpid()))
def run(cmd):return subprocess.run(cmd,cwd=R,capture_output=True,text=True)
def notify(message):
 p=run(['/home/lmxxf/.local/bin/herdr','agent','prompt','wM:p1',message]);(R/'notification.json').write_text(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr},ensure_ascii=False))
while True:
 q=run(['ssh','-o','ConnectTimeout=10',remote,'cat',base+'pipeline_status.json'])
 if q.returncode:
  (R/'sync_last_error.txt').write_text(q.stderr);time.sleep(30);continue
 try:s=json.loads(q.stdout)
 except ValueError:time.sleep(5);continue
 run(['rsync','-a','--include=/*.json','--exclude=/*/', '--exclude=*',remote+':'+base,str(R)+'/'])
 for parity in ['even','odd']:
  if parity=='odd' and s['status'] not in ['merging','evaluating','complete']:
   z=run(['ssh','-o','ConnectTimeout=10',remote,'ssh','-o','ConnectTimeout=10','169.254.30.81','cat',base+'fit_odd/convergence.jsonl'])
   if z.returncode==0:(R/'convergence_odd.jsonl').write_text(z.stdout)
   continue
  run(['scp',remote+':'+base+f'fit_{parity}/convergence.jsonl',str(R/f'convergence_{parity}.jsonl')])
 run([sys.executable,str(R/'build_report.py')])
 if s['status']=='failed':
  notify('闇：365 J-lens 后台流水线遇到错误，已保留断点与日志，请查看 grocery-haven/wechat-365-jlens-fit/pipeline_status.json。');break
 if s['status']=='complete':
  # Fetch snapshots once, after all producers have exited. Retrying rsync is safe.
  copy=run(['rsync','-a','--partial','--include=/lens_n*.pt','--exclude=*',remote+':'+base,str(R)+'/'])
  if copy.returncode:
   (R/'sync_last_error.txt').write_text(copy.stderr);time.sleep(30);continue
  final=R/'Qwen3.8-27B_jacobian_lens.pt'
  if not final.exists():final.symlink_to('lens_n100.pt')
  run(['rsync','-a','--include=/*.log','--include=/resource_timeseries*.jsonl','--exclude=/*/','--exclude=*',remote+':'+base,str(R)+'/'])
  plot=run([sys.executable,str(R/'plot_results.py')]);report=run([sys.executable,str(R/'build_report.py')])
  if plot.returncode or report.returncode:
   (R/'sync_last_error.txt').write_text(plot.stderr+'\n'+report.stderr);time.sleep(30);continue
  if not json.loads((R/'results.json').read_text()).get('complete'):
   time.sleep(30);continue
  notify('闇已完成 Qwen3.8-27B 全63层、100条中英双语 J-lens 拟合、快照收敛与官方题集评测；镜头、JSON、SVG和实验报告已同步至 /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-365-jlens-fit/。请核对实验报告里的实测数字与局限。')
  break
 time.sleep(30)
