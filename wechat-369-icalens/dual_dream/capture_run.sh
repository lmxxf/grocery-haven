#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export TRITON_CACHE_DIR="${TASK_ROOT}/triton_cache"
export TORCHINDUCTOR_CACHE_DIR="${TASK_ROOT}/dual_dream/torchinductor_cache"
export OPENBLAS_NUM_THREADS=8 OMP_NUM_THREADS=8
exec /home/lmxxf/work/interp-curvature-exp/venv/bin/python "${TASK_ROOT}/dual_dream_capture.py"
