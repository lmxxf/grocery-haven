"""Flush each sample immediately, including for sub-minute video jobs."""
import argparse
import csv
from datetime import datetime
from pathlib import Path
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument("output", type=Path)
a = p.parse_args()
with a.output.open("w", newline="", buffering=1) as f:
    while True:
        start = time.monotonic()
        result = subprocess.run([
            "nvidia-smi", "--query-gpu=timestamp,memory.used,utilization.gpu,power.draw,temperature.gpu",
            "--format=csv,noheader,nounits"
        ], capture_output=True, text=True, check=True)
        f.write(result.stdout)
        f.flush()
        time.sleep(max(0, 0.5 - (time.monotonic() - start)))
