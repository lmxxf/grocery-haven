#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/ica-lens-qwen38-27b
py=/home/lmxxf/work/interp-curvature-exp/venv/bin/python
while true; do
 mainstate=$($py -c 'import json;print(json.load(open("status.json"))["state"])')
 slavestate=$(ssh -o BatchMode=yes 169.254.30.81 cat /home/lmxxf/work/ica-lens-qwen38-27b/status.json | "$py" -c 'import sys,json;print(json.load(sys.stdin)["state"])')
 printf '%s main=%s slave=%s\n' "$(date -Iseconds)" "$mainstate" "$slavestate"
 if [[ "$mainstate" == failed || "$slavestate" == failed ]]; then exit 2; fi
 if [[ "$mainstate" == complete && "$slavestate" == complete ]]; then break; fi
 sleep 30
done
rsync -a --include='/L[0-9][0-9]/' --exclude='/[^L]*' --exclude=fit.npy --exclude=heldout.npy --exclude='*.tmp' lmxxf@169.254.30.81:/home/lmxxf/work/ica-lens-qwen38-27b/ ./
if [[ ! -f polysemy_capture.json ]]; then "$py" run_guarded.py collect_polysemy.py; fi
OPENBLAS_NUM_THREADS=4 "$py" posthoc_polysemy.py
printf 'POSTHOC_POLYSEMY_DONE\n'
