#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/icalens-v3-exp1b-archaic-nucai-20261116
PYTHON=/home/lmxxf/work/interp-curvature-exp/venv/bin/python
"$PYTHON" prepare_exp1b.py > prepare.log 2>&1
touch analysis.ready
"$PYTHON" run_exp1b.py > run.log 2>&1
"$PYTHON" supplement_same_layer.py > supplement_same_layer.log 2>&1
"$PYTHON" finalize_exp1b.py
