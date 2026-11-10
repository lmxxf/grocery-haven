import sys,json
from pathlib import Path
r=Path(__file__).resolve().parent
try:
 state=json.loads((r/'fit_odd/state.json').read_text())
 pid=json.loads((r/'watchdog.json').read_text())['pid']
 done=state.get('completed')==50 and (r/'fit_odd/lens_local_n50.pt').exists() and not Path('/proc/'+str(pid)).exists()
except (OSError,ValueError):done=False
sys.exit(0 if done else 1)
