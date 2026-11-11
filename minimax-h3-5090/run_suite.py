"""Run full H3 acceptance jobs on the already started Windows service."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import time

from h3_generate import request

ROOT = Path(__file__).resolve().parent
WAN = ROOT.parent / "wan22-5090"
sys.path.insert(0, str(WAN))
from remote_ps import run as windows

SERVER = "http://192.168.31.50:8188"
BASE = r"C:\AI\Wan22-ComfyUI"


def wait_models(mode, turbo):
    from h3_generate import TURBO
    manifest = json.loads((ROOT / "h3_manifest.json").read_text())
    paths = [
        item["path"] for item in manifest
        if item["path"].startswith(("vae/", "text_encoders/"))
        or f"minimax_h3_{mode}_pruned" in item["path"]
        or (turbo and item["path"].endswith(TURBO[mode, turbo]))
    ]
    condition = " -and ".join(
        f"(Test-Path '{BASE}\\ComfyUI_windows_portable\\ComfyUI\\models\\{path}')"
        for path in paths
    )
    status = f"{BASE}\\logs\\h3_download_status.json"
    while True:
        probe = windows(
            f"if({condition}){{'READY'}}else{{Get-Content '{status}' -Raw}}",
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if probe == "READY":
            return
        try:
            state = json.loads(probe)
        except json.JSONDecodeError:
            time.sleep(5)
            continue
        if state.get("state") == "failed":
            raise RuntimeError(state["error"])
        time.sleep(25)


def case(name, mode, turbo=None, references=(), frames=(), duration=6):
    folder = ROOT / "outputs" / name
    if (folder / "result.json").exists():
        return json.loads((folder / "result.json").read_text())
    wait_models(mode, turbo)
    folder.mkdir(parents=True, exist_ok=True)
    for attempt in range(180):
        try:
            queue = request(SERVER, "/queue")
            if not queue["queue_running"] and not queue["queue_pending"]:
                break
        except OSError:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("ComfyUI did not become idle and ready")
    print(f"RUN {name}", flush=True)
    windows(f"& '{BASE}\\scripts\\h3_monitor_start.ps1' -Name '{name}'", check=True)
    command = [
        sys.executable, str(ROOT / "h3_generate.py"), "--mode", mode,
        "--prompt-file", str(ROOT / "prompts" / ("anchored.txt" if frames else mode + ".txt")),
        "--seed", "20261111", "--duration", str(duration), "--output-dir", str(folder),
    ]
    if turbo:
        command.extend(["--turbo", str(turbo)])
    if references:
        command.extend(["--ref-images", *map(str, references)])
    if frames:
        command.extend(["--frames-images", *map(str, frames)])
    try:
        subprocess.run(command, check=True)
    finally:
        windows("Stop-ScheduledTask -TaskName 'H3-GPU-Monitor'", check=True)
    gpu_log = ROOT / "logs" / f"gpu_{name}.csv"
    subprocess.run([
        sys.executable, str(WAN / "download_file.py"),
        f"C:/AI/Wan22-ComfyUI/logs/gpu_{name}.csv", str(gpu_log)
    ], check=True)
    rows = list(csv.reader(gpu_log.read_text(encoding="utf-8-sig").splitlines()))
    job = max(folder.glob("job_*.json"), key=lambda p: p.stat().st_mtime)
    result = json.loads(job.read_text())
    result["peak_mib"] = max(float(row[1]) for row in rows if len(row) > 1 and row[1].strip().isdigit())
    (folder / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"DONE {name} {result.get('server_seconds')} sec {result['peak_mib']} MiB", flush=True)
    return result


if __name__ == "__main__":
    first = case("fl2va_8", "fl2va", turbo=8)
    case("fl2va_4_anchors", "fl2va", turbo=4, frames=(first["keyframes"][0], first["keyframes"][-1]), duration=5)
    refs = (first["keyframes"][0], ROOT / "courtyard.png")
    case("ref2va_4", "ref2va", turbo=4, references=refs)
    case("ref2va_20", "ref2va", references=refs)
