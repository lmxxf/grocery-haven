#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/curvature-icml2026-361
export OPENBLAS_NUM_THREADS=8
py=/home/lmxxf/work/interp-curvature-exp/venv/bin/python
for model in pythia-2.8b gpt2-xl; do
 while [ ! -f "download_${model}.json" ]; do sleep 5; done
 "$py" run_reproduction.py --model "$model" --pert-tokens 32
done
