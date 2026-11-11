"""Copy an authorized C:\\AI artifact via Spark without direct Windows credentials."""
import subprocess,shlex,sys
from pathlib import Path
p=sys.argv[1];out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
win='rtx5090:'+p.replace('\\','/');staging='/home/lmxxf/work/wan22-5090/'+out.name
subprocess.run(['ssh','lmxxf@192.168.31.198','scp '+shlex.quote(win)+' '+shlex.quote(staging)],check=True)
subprocess.run(['scp','lmxxf@192.168.31.198:'+staging,str(out)],check=True)
