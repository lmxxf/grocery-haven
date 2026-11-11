#!/usr/bin/env python3
"""Batch render all 18 clips of the 3-minute anime drama on RTX 5090 using MiniMax-H3 Ref2VA 4-step Turbo."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/minimax-h3-5090')
DRAMA = ROOT / 'drama_project'
CLIPS_OUT = DRAMA / 'clips_raw'
CLIPS_OUT.mkdir(parents=True, exist_ok=True)

manifest = json.loads((DRAMA / 'manifest.json').read_text(encoding='utf-8'))
status_file = DRAMA / 'render_progress.json'
progress = json.loads(status_file.read_text(encoding='utf-8')) if status_file.exists() else {}

t_all = time.time()
for idx, item in enumerate(manifest, 1):
    cid = item['id']
    done_mp4 = CLIPS_OUT / f"{cid}.mp4"
    if done_mp4.exists() and done_mp4.stat().st_size > 100_000:
        print(f"[{idx:02d}/18] {cid} already exists ({done_mp4.stat().st_size/1e6:.2f} MB), skipping.", flush=True)
        continue

    shot_dir = CLIPS_OUT / cid
    shot_dir.mkdir(parents=True, exist_ok=True)
    ref_paths = [str(DRAMA / r) for r in item['refs']]
    prompt_path = str(DRAMA / item['prompt_file'])
    seed = 20261100 + idx

    cmd = [
        sys.executable, str(ROOT / 'h3_generate.py'),
        '--mode', 'ref2va',
        '--turbo', '4',
        '--duration', str(item['duration']),
        '--width', '1024',
        '--height', '576',
        '--seed', str(seed),
        '--prompt-file', prompt_path,
        '--output-dir', str(shot_dir),
        '--ref-images', *ref_paths
    ]
    print(f"\n=== [{idx:02d}/18] Rendering {cid} (10s -> 243f @ 1024x576, refs={len(ref_paths)}) ===", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if proc.returncode != 0:
        print(f"ERROR on {cid}:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}", flush=True)
        # Retry once with 832x480 if 1024x576 hits VRAM ceiling on 3-ref 243 frames
        print(f"Retrying {cid} at 832x480 (upscaled cleanly during final master)...", flush=True)
        cmd_fb = [
            sys.executable, str(ROOT / 'h3_generate.py'),
            '--mode', 'ref2va',
            '--turbo', '4',
            '--duration', str(item['duration']),
            '--width', '832',
            '--height', '480',
            '--seed', str(seed + 100),
            '--prompt-file', prompt_path,
            '--output-dir', str(shot_dir),
            '--ref-images', *ref_paths
        ]
        t0 = time.time()
        proc = subprocess.run(cmd_fb, capture_output=True, text=True)
        dt = time.time() - t0
        if proc.returncode != 0:
            raise RuntimeError(f"Both attempts failed on {cid}: {proc.stderr}")

    mp4_line = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip().endswith('.mp4')][-1]
    src_mp4 = Path(mp4_line)
    src_mp4.replace(done_mp4)
    progress[cid] = {"mp4": str(done_mp4), "seconds": round(dt, 2), "size_mb": round(done_mp4.stat().st_size / 1e6, 2)}
    status_file.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f" -> [{idx:02d}/18] {cid} DONE in {dt:.1f}s -> {done_mp4} ({progress[cid]['size_mb']} MB)", flush=True)

print(f"\nALL 18 CLIPS FINISHED in {(time.time()-t_all)/60:.1f} min!", flush=True)
