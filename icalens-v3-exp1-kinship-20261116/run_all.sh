#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/icalens-v3-exp1-kinship-20261116
PYTHON=/home/lmxxf/work/interp-curvature-exp/venv/bin/python
"$PYTHON" run_exp1a.py > run.log 2>&1
