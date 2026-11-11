#!/usr/bin/env python3
"""Assemble the 64-layer oriented ICA-Lens repository in official `icalens` v0.4.0 format."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import load_file, save_file

ROOT = Path("/home/lmxxf/work/ica-lens-qwen38-27b")
sys.path.insert(0, str(ROOT / "icalens_pkg"))
from icalens import ICALens  # noqa: E402

OUT = ROOT / "hf_release"
ART_DIR = OUT / "artifacts" / "resid_post"
ART_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    base_manifest = json.loads((ROOT / "L00" / "native" / "icalens.json").read_text(encoding="utf-8"))
    merged_layers: dict[str, dict] = {}

    for layer in range(64):
        l_dir = ROOT / f"L{layer:02d}"
        m_layer = json.loads((l_dir / "native" / "icalens.json").read_text(encoding="utf-8"))
        entry = m_layer["layers"][str(layer)]

        ori = load_file(str(l_dir / "oriented.safetensors"))
        center = ori["center"].contiguous()
        reading = ori["components"].contiguous()
        writing = ori["mixing"].contiguous()

        assert center.shape == (5120,) and center.dtype == torch.float32
        assert reading.shape == (5120, 5120) and reading.dtype == torch.float32
        assert writing.shape == (5120, 5120) and writing.dtype == torch.float32
        assert torch.isfinite(center).all() and torch.isfinite(reading).all() and torch.isfinite(writing).all()

        # Quick dual check on first 16 rows: reading[:16] @ writing[:, :16] == I_16
        eye_err = (reading[:16] @ writing[:, :16] - torch.eye(16)).abs().max().item()
        assert eye_err < 1e-4, f"Layer {layer} biorthogonality error too high: {eye_err}"

        rel_file = f"artifacts/resid_post/layer_{layer:02d}.safetensors"
        out_path = OUT / rel_file
        save_file(
            {
                "center": center,
                "reading_matrix": reading,
                "writing_matrix": writing,
            },
            str(out_path),
        )

        entry = dict(entry)
        entry["file"] = rel_file
        prov = dict(entry["fitting"].get("provenance") or {})
        prov["orientation"] = "fit_skewness_nonnegative (both reading rows and writing columns multiplied by sign(fit_skewness))"
        prov["source_weights"] = "Qwen/Qwen3.8-27B-FP8 dequantized blockwise (128x128) to BF16"
        prov["bilingual_corpus"] = "1:1 token-balanced English WikiText-103 + Chinese Wikipedia (200,704 fit tokens, 51,200 heldout tokens)"
        entry["fitting"] = dict(entry["fitting"])
        entry["fitting"]["provenance"] = prov
        entry["fitting"]["component_id_convention"] = "descending absolute contrast deviation from Gaussian; C0 is strongest; signs canonicalized to nonnegative fit skewness (zero keeps +1)"
        merged_layers[str(layer)] = entry

        if layer % 8 == 0 or layer == 63:
            print(f"[build_hf_release] wrote layer {layer:02d} (eye16 max_err={eye_err:.2e})", flush=True)

    manifest = dict(base_manifest)
    manifest["model"] = {
        "repo_id": "Qwen/Qwen3.8-27B",
        "revision": None,
        "type": "instruct",
    }
    manifest["layers"] = merged_layers

    (OUT / "icalens.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Smoke test via official ICALens.from_pretrained
    lens = ICALens.from_pretrained(OUT)
    assert list(lens.available_layers) == list(range(64)), f"Unexpected layers: {lens.available_layers}"
    rng = np.random.default_rng(369)
    dummy = rng.standard_normal((4, 5120)).astype(np.float32)
    for test_layer in (0, 32, 41, 63):
        scores = lens.transform(dummy, layer=test_layer)
        recon = lens.inverse_transform(scores, layer=test_layer)
        dummy_unit = dummy / np.linalg.norm(dummy, axis=-1, keepdims=True)
        rec_err = float(np.max(np.abs(recon - dummy_unit)))
        assert rec_err < 1e-4, f"Layer {test_layer} inverse_transform error: {rec_err}"
        print(f"[smoke_test] layer {test_layer:02d} transform+inverse_transform max_err={rec_err:.2e}", flush=True)

    print("BUILD_AND_SMOKE_OK", flush=True)


if __name__ == "__main__":
    main()
