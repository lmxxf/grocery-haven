"""Stage the pinned FL2VA backbone on Spark, with the same published digest."""
import hashlib
import json
from pathlib import Path
from huggingface_hub import hf_hub_download

root = Path(__file__).resolve().parent
entry = next(f for f in json.loads((root / "h3_manifest.json").read_text()) if "fl2va_pruned" in f["path"])
path = Path(hf_hub_download(entry["repository"], entry["path"], revision=entry["revision"], local_dir=root / "weights"))
assert path.stat().st_size == entry["size"]
digest = hashlib.sha256()
with path.open("rb") as source:
    for block in iter(lambda: source.read(16 * 1024 * 1024), b""):
        digest.update(block)
assert digest.hexdigest() == entry["sha256"]
print("VERIFIED", path, flush=True)
