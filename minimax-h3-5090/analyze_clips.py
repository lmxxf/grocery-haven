"""CPU-only health and channel statistics for the acceptance videos."""
import csv
import json
from pathlib import Path
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parent
for folder in sorted((ROOT / "outputs").iterdir()):
    result_file = folder / "result.json"
    if not result_file.exists():
        continue
    result = json.loads(result_file.read_text())
    pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", result["video"], "-map", "0:a:0", "-f", "f32le", "-"])
    audio = np.frombuffer(pcm, dtype="<f4").reshape(-1, 2)
    audio_stats = {
        "rms_per_channel": np.sqrt(np.mean(audio.astype(np.float64) ** 2, axis=0)).tolist(),
        "peak_absolute": float(np.abs(audio).max()),
        "stereo_difference_rms": float(np.sqrt(np.mean((audio[:, 0] - audio[:, 1]) ** 2))),
        "over_full_scale_fraction": float(np.mean(np.abs(audio) > 1.0)),
    }
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", result["video"], "-vf", "scale=128:72",
        "-vsync", "0", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"
    ])
    rgb = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 72, 128, 3).astype(np.float32)
    luma = rgb @ np.array([0.2126, 0.7152, 0.0722])
    means = luma.mean(axis=(1, 2))
    stds = luma.std(axis=(1, 2))
    assert np.isfinite(audio).all() and means.min() > 2 and stds.min() > 2
    gpu_log = ROOT / "logs" / f"gpu_{folder.name}.csv"
    rows = list(csv.reader(gpu_log.read_text(encoding="utf-8-sig").splitlines()))
    result["audio_checks"] = audio_stats
    result["video_checks"] = {
        "decoded_frames": len(rgb), "minimum_mean_luma": float(means.min()),
        "minimum_spatial_std_luma": float(stds.min()),
        "mean_adjacent_frame_RGB_MAE": float(np.abs(np.diff(rgb, axis=0)).mean()),
    }
    result["gpu_sampling"] = {
        "rows": len(rows), "first_timestamp": rows[0][0], "last_timestamp": rows[-1][0],
        "target_interval_seconds": 0.5, "method": "one-shot NVML via nvidia-smi with per-row flush",
    }
    assert len(rows) >= result["server_seconds"] * 0.8
    result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(folder.name, result["video_checks"], audio_stats, flush=True)
