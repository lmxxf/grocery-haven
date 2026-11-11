import subprocess,sys,shlex
from pathlib import Path
R=Path(__file__).resolve().parent
for arg in sys.argv[1:]:
 p=Path(arg).resolve();name=p.name
 subprocess.run(['scp',str(p),'lmxxf@192.168.31.198:/home/lmxxf/work/wan22-5090/'+name],check=True)
 cmd='scp '+shlex.quote('/home/lmxxf/work/wan22-5090/'+name)+' '+shlex.quote('rtx5090:C:/AI/Wan22-ComfyUI/scripts/'+name)
 subprocess.run(['ssh','lmxxf@192.168.31.198',cmd],check=True)
