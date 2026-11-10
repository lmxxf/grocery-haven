---
license: apache-2.0
base_model: Qwen/Qwen3.8-27B
tags:
  - interpretability
  - jacobian-lens
  - j-lens
  - j-space
  - mechanistic-interpretability
  - qwen3.8
  - bilingual
language:
  - en
  - zh
---

# Qwen3.8-27B Bilingual Jacobian Lens (`N=100`, 50 EN + 50 ZH)

Precomputed full-layer **Jacobian Lens (J-lens)** for **`Qwen/Qwen3.8-27B`** (64 layers, `d_model = 5120`, hybrid 48 Gated DeltaNet linear-attention layers + 16 full-attention layers), fitted using Anthropic's official [`anthropics/jacobian-lens`](https://github.com/anthropics/jacobian-lens) estimator (`commit 581d3986`).

Unlike English-only precomputed lenses, this checkpoint is fitted on a **strictly 1:1 bilingual corpus** (**50 English WikiText-103 passages + 50 Chinese Wikipedia passages**, `N = 100` total, `seq_len = 128`, `skip_first = 16`, `111` valid positions per passage, `256,000` full-network backward passes across two NVIDIA DGX Spark GB10 nodes).

---

## Checkpoint Specifications

- **File**: `Qwen3.8-27B_jacobian_lens.pt` (`3.30 GB` / `3.08 GiB`, SHA256: `e9b11582f2023b7934ed591ab1134f7a3a9b6d64782665d3400a3fc56f532402`)
- **Source Layers**: `0 .. 62` (63 full `5120 × 5120` matrices stored in `float16`, accumulated in `float32`)
- **Target Layer**: `63` (final transformer block output prior to `FinalRMSNorm` and `lm_head`)
- **Estimator**: Official future-sum Jacobian mean $J_\ell[i,j] = \mathbb{E}_p \sum_{q \ge p} \frac{\partial h_{63}[q, i]}{\partial h_\ell[p, j]}$

---

## Quick Start

```python
import torch
from jacobian_lens import JacobianLens

# Load directly with jacobian-lens or torch.load
lens_ckpt = torch.load("Qwen3.8-27B_jacobian_lens.pt", map_location="cpu")
# lens_ckpt["J"] is a dict mapping source layer index (0..62) -> [5120, 5120] float16 tensor
J_38 = lens_ckpt["J"][38].float()

# Project layer-38 residual stream h_38 [..., 5120] to the final layer readout space:
# h_proj = h_38 @ J_38.T
# logits = lm_head(final_rms_norm(h_proj))
```

---

## Benchmark Evaluation (`Multihop` & `Multilingual`)

Evaluated on the official `anthropics/jacobian-lens` benchmarks adapted to single-token targets in the Qwen vocabulary (`248,320` tokens):

| Lens Stage | Multihop `pass@1` | Multihop `pass@5` | Multilingual `pass@1` | Multilingual `pass@5` |
|:---|:---:|:---:|:---:|:---:|
| **Vanilla (Logit Lens, $J=I$)** | 33.93% | 53.97% | 21.26% | 38.86% |
| **`N=1` (1 EN passage)** | 33.93% | 56.35% | **32.09%** | **42.68%** |
| **`N=10` (5 EN + 5 ZH)** | 33.33% | 57.54% | 26.01% | 39.64% |
| **`N=20` (10 EN + 10 ZH)** | 32.14% | **58.73%** | 26.01% | 40.34% |
| **`N=50` (25 EN + 25 ZH)** | 35.12% | 57.54% | 23.91% | 39.64% |
| **`N=100` (50 EN + 50 ZH)** | **36.31%** | 56.35% | 25.08% | 40.58% |

### Representative Bilingual Readout & Lens-Coordinate Swap

- **Chinese Boot-Country Currency Prompt** (`常识：形状像一只靴子的欧洲国家使用的法定货币是`):
  - **Vanilla Logit Lens (Layer 41)**: `'意大利'` at Rank `131`, `'Italy'` at Rank `104`
  - **`N=100` Bilingual J-lens (Layer 41)**: Top-5 tokens are **`['意大利', ' Italy', ' Italian', 'Italy', ' Italia']`** (`'意大利'` Rank **1**, `' Italy'` Rank **2**)
- **Causal Lens-Coordinate Swap (`L34–L44`)**:
  - On `Fact: The currency used in the country shaped like a boot is`, swapping `Italy / 意大利 -> Japan / 日本` using the `N=100` lens dictionary flips the greedy output from `" the euro."` to **`" the yen."`** (even when swapping only the Chinese `'意大利' -> '日本'` direction on the pure English prompt), whereas Vanilla and `N=1` dictionaries fail to flip the output.
