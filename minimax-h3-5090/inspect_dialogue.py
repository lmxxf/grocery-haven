"""CPU-only Mandarin speech transcription for the acceptance clips."""
import json
import os
from pathlib import Path
import sys
import time

os.environ["CUDA_VISIBLE_DEVICES"] = ""
import torch
import whisper

root = Path(__file__).resolve().parent
torch.set_num_threads(8)
first = root / "outputs" / sys.argv[1] / "result.json"
while not first.exists():
    time.sleep(5)
model = whisper.load_model(str(Path.home() / ".cache/whisper/large-v3.pt"), device="cpu")
for name in sys.argv[1:]:
    folder = root / "outputs" / name
    while not (folder / "result.json").exists():
        time.sleep(5)
    result = json.loads((folder / "result.json").read_text())
    transcript = model.transcribe(
        result["video"], language="zh", task="transcribe",
        fp16=False, temperature=0, condition_on_previous_text=False,
    )
    data = {
        "text": transcript["text"],
        "segments": [
            {key: segment[key] for key in ("start", "end", "text", "avg_logprob", "no_speech_prob")}
            for segment in transcript["segments"]
        ],
        "device": "cpu",
        "model": "Whisper large-v3",
    }
    (folder / "dialogue_asr.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(name, data["text"], flush=True)
