"""Switch the existing manual task without adding an automatic startup trigger."""
import argparse
import json
import sys
import time
from pathlib import Path
from h3_generate import request

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "wan22-5090"))
from remote_ps import run

p = argparse.ArgumentParser()
p.add_argument("backend", choices=["sdpa", "sage"])
a = p.parse_args()
server = "http://192.168.31.50:8188"
queue = request(server, "/queue")
if queue["queue_running"] or queue["queue_pending"]:
    raise RuntimeError("Wait for the active queue before changing backend")
run(r"""
$b='C:\AI\Wan22-ComfyUI'
Stop-ScheduledTask -TaskName 'Wan22-ComfyUI'
if(Test-Path "$b\logs\comfy.pid"){
 $i=[int](Get-Content "$b\logs\comfy.pid")
 $p=Get-CimInstance Win32_Process -Filter "ProcessId=$i" -ErrorAction SilentlyContinue
 if($p -and $p.ExecutablePath -like "$b\*"){Stop-Process -Id $i -Force -ErrorAction SilentlyContinue}
}
@{backend='BACKEND';listen='0.0.0.0';port=8188} | ConvertTo-Json | Set-Content "$b\server_config.json" -Encoding UTF8
Start-ScheduledTask -TaskName 'Wan22-ComfyUI'
""".replace("BACKEND", a.backend), check=True)
for attempt in range(180):
    try:
        stats = request(server, "/system_stats")
        if ("--use-sage-attention" in stats["system"]["argv"]) == (a.backend == "sage"):
            print("BACKEND_READY", a.backend)
            break
    except OSError:
        pass
    time.sleep(1)
else:
    raise RuntimeError("Backend did not become ready")
