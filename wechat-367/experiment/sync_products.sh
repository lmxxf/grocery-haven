#!/usr/bin/env bash
set -euo pipefail
root=/home/lmxxf/work/ica-lens-qwen38-27b
localroot=/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-367/experiment
# Only products; no activations, model files, Triton cache or J-lens checkpoint.
ssh lmxxf@192.168.31.198 "rsync -a --include='/L[0-9][0-9]/' --exclude='/[^L]*' --exclude=fit.npy --exclude=heldout.npy --exclude='*.tmp' lmxxf@169.254.30.81:$root/ $root/"
rsync -a --include='/L[0-9][0-9]/' --exclude='/[^L]*' --exclude=fit.npy --exclude=heldout.npy --exclude='*.tmp' lmxxf@192.168.31.198:$root/ "$localroot/"
