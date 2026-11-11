---
license: apache-2.0
library_name: icalens
base_model:
  - Qwen/Qwen3.8-27B
  - Qwen/Qwen3.8-27B-FP8
tags:
  - interpretability
  - independent-component-analysis
  - ica-lens
  - icalens
  - mechanistic-interpretability
  - qwen3.8
  - bilingual
  - arxiv:2606.11722
language:
  - en
  - zh
---

# Qwen3.8-27B Bilingual ICA Lens (All 64 Layers, 1:1 EN + ZH)

Precomputed full-model **ICA Lens** (`327,680` layer-component pairs across all **64 layers**, `d_model = 5120`) for **`Qwen/Qwen3.8-27B`** / **`Qwen/Qwen3.8-27B-FP8`** (48 Gated DeltaNet linear-attention layers + 16 full-attention layers), fitted with the official [`icalens`](https://pypi.org/project/icalens/) (`v0.4.0`) estimator ([arXiv:2606.11722](https://arxiv.org/abs/2606.11722)).

This checkpoint pairs directly with our precomputed bilingual Jacobian Lens **[`lmxxf/Qwen3.8-27B-jacobian-lens`](https://huggingface.co/lmxxf/Qwen3.8-27B-jacobian-lens)** (`N=100`, 50 EN + 50 ZH) for joint **`ICA-Lens × J-lens`** vocabulary readout across intermediate layers.

---

## Highlights & Key Empirical Findings

- **Strictly 1:1 Bilingual Fitting & Held-Out Verification**:
  - Fitted on **200,704 tokens** (1:1 token-balanced English WikiText-103 + Chinese Wikipedia, document-isolated windows $\le 512$) and evaluated on **51,200 unseen held-out tokens** across two NVIDIA DGX Spark (GB10) nodes (`132.9` minutes total wall time).
  - Symmetric FastICA (`logcosh`, 50 iterations, row-$L_2$ input normalization, `FP64` covariance accumulation).
  - **Skewness-Oriented Signs**: Every component's `reading_matrix` row and `writing_matrix` column are co-flipped by $\operatorname{sign}(\text{skew}_{\text{fit}})$ so that fit skewness is nonnegative (zero skewness keeps sign `+1`) while preserving reconstruction of the **row-normalized** input ($u = h / \max(\|h\|_2, 10^{-12})$, $y = C(u-c)$, $\hat{u} = M y + c$, component ranking IDs `C0..C5119` unchanged).
- **64-Layer Non-Gaussian Hourglass Landscape** (on 51,200 unseen held-out tokens):
  - **`274,451 / 327,680` (`83.76%`)** axes exceed excess kurtosis $\kappa > 1$; **`144,450 / 327,680` (`44.08%`)** exceed $\kappa > 10$ (global median $\kappa = 6.20$, 99th percentile $\kappa = 815.97$).
  - Clear three-stage profile: sharp lexical islands at entry (`L0`: `5,058` axes with $\kappa > 10$, median `130.87`) $\rightarrow$ dense mixing valley at mid-network (`L32`: `1,251` axes with $\kappa > 10$, median `0.99`) $\rightarrow$ late re-crystallization (`L54`: `2,828` axes with $\kappa > 10$, median `15.24`).
- **Cross-Lingual Polysemy Alignment (`apple` vs. `苹果`)**:
  - Under causal last-token evaluation (no right-context leakage), blind single-axis selection on pure English lowercase `apple` (fruit vs. tech company) and pure Chinese `苹果` (fruit vs. tech company) independently selects **the exact same axis ID out of 5,120 unsupervised axes in 42 out of 64 layers** (peaking at cosine `0.879` in `L7`, `8/8` held-out accuracy in 55 English layers and 56 Chinese layers).
- **Joint `ICA-Lens × J-lens` Readout**:
  - Replacing naive `Logit Lens` ($J = I$) with `lmxxf/Qwen3.8-27B-jacobian-lens` changes `81.5%` of Top-5 vocabulary tokens across 6,633 candidate axes (`99.81%` at `L0`), turning subword fragments into clean multilingual synonym sets (e.g., `L0/C2108`: `eck / 姗 / rast` $\rightarrow$ **`对于 / for / для / für`**; `L41/C1051` $\rightarrow$ **`someone / 某人`**; `L41/C828` $\rightarrow$ **`种植 / 作物 / crops / 蔬菜`**).

---

## Quick Start

Install the official release first: `pip install "icalens==0.4.0"`.

### 1. Native `icalens` Loading (On-Demand Per-Layer Download)

`ICALens.from_pretrained` downloads only `icalens.json` upfront and fetches individual `layer_XX.safetensors` (`200 MiB` each) lazily when requested:

```python
import numpy as np
from icalens import ICALens

lens = ICALens.from_pretrained("lmxxf/Qwen3.8-27B-ica-lens")
print("Available layers:", lens.available_layers)  # layers 0 through 63

# Transform externally captured residual-stream activations h [seq_len, 5120] at layer 41:
# (lens.transform automatically applies row-L2 normalization as specified in icalens.json)
h_layer41 = np.random.default_rng(0).standard_normal((4, 5120)).astype(np.float32)
# Replace this synthetic input with your captured activations.
scores = lens.transform(h_layer41, layer=41)  # [seq_len, 5120] signed ICA coordinates
```

### 2. Joint `ICA-Lens × Jacobian Lens` Vocabulary Readout

Combine any ICA writing direction `M[:, j]` with [`lmxxf/Qwen3.8-27B-jacobian-lens`](https://huggingface.co/lmxxf/Qwen3.8-27B-jacobian-lens):

```python
import torch
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file

# 1. Load Layer-41 ICA writing matrix M [5120, 5120]
ica_l41 = load_file(
    hf_hub_download("lmxxf/Qwen3.8-27B-ica-lens", "artifacts/resid_post/layer_41.safetensors")
)
d_c828 = ica_l41["writing_matrix"][:, 828]  # Qualitative plant/crop candidate axis C828

# 2. Transport to final layer via N=100 Bilingual Jacobian Lens J_41 [5120, 5120]
jlens = torch.load(
    hf_hub_download("lmxxf/Qwen3.8-27B-jacobian-lens", "Qwen3.8-27B_jacobian_lens.pt"),
    map_location="cpu", weights_only=True, mmap=True,
)
J_41 = jlens["J"][41].float()
d_final = J_41 @ d_c828  # [5120]

# 3. With the matching model loaded, apply its final RMSNorm and lm_head:
# text_model = model.model.language_model
# logits = model.lm_head(text_model.norm(d_final.to(text_model.norm.weight.dtype)))
# Equivalent float32 norm: d_final * rsqrt(mean(d_final**2) + 1e-6) * (1 + norm_weight)
# Top tokens from our FP8-dequantized BF16 experiment: ['种植', '作物', '和蔬菜', ' crops', '蔬菜', '植物']
```

---

This is a heuristic writing-direction readout: J-lens was fitted on raw residuals while ICA normalizes each input row. Vocabulary changes are not an interpretability accuracy metric. The synthetic polysemy holdout has only eight examples per comparison; repeated layers are not independent trials. Fifty fixed ICA iterations do not guarantee convergence, and high kurtosis alone is not a semantic label or proof of independence.

At layer 63 use the identity mapping; the J-lens checkpoint stores matrices only for layers 0–62.

## Repository Structure

- `icalens.json`: Official `icalens` format v4 manifest covering layers `0..63`.
- `artifacts/resid_post/layer_00.safetensors` .. `layer_63.safetensors`: Per-layer `float32` tensors (`center` `[5120]`, `reading_matrix` `[5120, 5120]`, `writing_matrix` `[5120, 5120]`, `200.02 MiB` per layer, `12.50 GiB` total).

---

## Citation

If you use this precomputed lens or the bilingual `ICA-Lens × J-lens` findings, please cite the ICA Lens paper:

```bibtex
@article{liu2026icalens,
  title={ICA Lens: Interpreting Language Models Without Training Another Dictionary},
  author={Liu, Sida and Han, Feijiang},
  journal={arXiv preprint arXiv:2606.11722},
  year={2026}
}
```
