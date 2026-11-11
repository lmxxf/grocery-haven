import os,sys,time,subprocess,signal,json
from pathlib import Path
R=Path(__file__).resolve().parent;os.chdir(R)
def avail():return int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))/1048576
subprocess.run(['sudo','-n','sh','-c','echo 3 > /proc/sys/vm/drop_caches'],check=True)
assert avail()>=100,avail()
p=subprocess.Popen([sys.executable,*sys.argv[1:]],start_new_session=True)
minimum=avail()
while p.poll()is None:
 minimum=min(minimum,avail())
 if avail()<20:os.killpg(p.pid,signal.SIGKILL);p.wait();raise RuntimeError('independent20GiB watchdog killed process group')
 time.sleep(.25)
(R/('postprocess_resource_'+Path(sys.argv[1]).stem+'.json')).write_text(json.dumps({'command':sys.argv[1:],'exit_code':p.returncode,'minimum_MemAvailable_GiB':minimum,'time':time.time()}))
sys.exit(p.returncode)
