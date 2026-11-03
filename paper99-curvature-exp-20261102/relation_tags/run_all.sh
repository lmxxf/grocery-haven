#!/usr/bin/env bash
set -euo pipefail
cd /home/lmxxf/work/interp-curvature-exp/relation_tags
export PYTHONUNBUFFERED=1
../venv/bin/python run_relation_tags.py --model Qwen3.5-35B-A3B-Base
../venv/bin/python run_relation_tags.py --model Qwen3-0.6B
../venv/bin/python run_relation_tags.py --model Qwen3.5-35B-A3B
