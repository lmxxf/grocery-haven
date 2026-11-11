"""Transfer the verified Spark checkpoint and validate the Windows copy."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parent / "wan22-5090"))
from remote_ps import run

entry = next(x for x in json.loads((root / "h3_manifest.json").read_text()) if "fl2va_pruned" in x["path"])
spark = "lmxxf@192.168.31.198"
staging = "/home/lmxxf/work/minimax-h3-5090"
source = f"{staging}/weights/{entry['path']}"
app = "C:/AI/Wan22-ComfyUI/ComfyUI_windows_portable/ComfyUI"
target = f"{app}/models/{entry['path']}"
while True:
    log = subprocess.check_output(["ssh", spark, "tail -5 " + staging + "/fetch_fl.log"], text=True)
    if "VERIFIED " in log:
        break
    if "Traceback" in log or "Error:" in log:
        raise RuntimeError(log)
    time.sleep(25)
parent = str(Path(target).parent)
run(f"New-Item -ItemType Directory -Force -Path '{parent}' | Out-Null", check=True)
subprocess.run(["ssh", spark, f"scp {shlex.quote(source)} {shlex.quote('rtx5090:' + target + '.part')}"], check=True)
run(f"""
$b='C:/AI/Wan22-ComfyUI'
$py="$b/ComfyUI_windows_portable/python_embeded/python.exe"
$info=& $py -s "$b/scripts/verify_sha256.py" '{target}.part' '{entry['sha256']}'
if($LASTEXITCODE -ne 0){{throw 'FL2VA checksum mismatch'}}
$info | Set-Content "$b/logs/h3_fl2va_transfer_verified.json" -Encoding UTF8
Move-Item '{target}.part' '{target}'
""", check=True)
print("WINDOWS_FL2VA_VERIFIED", flush=True)
