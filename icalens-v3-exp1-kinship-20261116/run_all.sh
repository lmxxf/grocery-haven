#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/ica-lens-qwen38-27b-v3/experiments/exp1a_kinship
PYTHON=/home/lmxxf/work/interp-curvature-exp/venv/bin/python
"$PYTHON" run_exp1a.py > run.log 2>&1
"$PYTHON" supplement_readouts.py > supplement_readouts.log 2>&1
"$PYTHON" refresh_statistics.py > refresh_statistics.log 2>&1
"$PYTHON" write_findings.py
