#!/usr/bin/env python3
"""Run PowerShell on the authorized 5090 via Spark; never uses local GPU."""
import base64,subprocess,sys,argparse
from pathlib import Path
SPARK='lmxxf@192.168.31.198'
def run(code,**kwargs):
 prefix="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);"
 encoded=base64.b64encode((prefix+'& {\n'+code+'\n}').encode('utf-16-le')).decode()
 return subprocess.run(['ssh','-o','BatchMode=yes',SPARK,'ssh -o BatchMode=yes rtx5090 powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -OutputFormat Text -EncodedCommand '+encoded],**kwargs)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('file');a=p.parse_args();sys.exit(run(Path(a.file).read_text()).returncode)
