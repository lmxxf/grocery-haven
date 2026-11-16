#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/icalens-v3-exp2-cot-navigation-20261117
PYTHON=/home/lmxxf/work/interp-curvature-exp/venv/bin/python
"$PYTHON" prepare_exp2.py
"$PYTHON" calibrate_exp2.py
touch analysis.ready
"$PYTHON" run_exp2.py > run.log 2>&1
"$PYTHON" final_audit_exp2.py
