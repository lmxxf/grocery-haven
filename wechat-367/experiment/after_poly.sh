#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/ica-lens-qwen38-27b
while [[ ! -f polysemy_summary.json ]]; do sleep 30; done
if [[ ! -f extra_readouts_complete.json ]]; then
 /home/lmxxf/work/interp-curvature-exp/venv/bin/python run_guarded.py extra_readouts.py
fi
