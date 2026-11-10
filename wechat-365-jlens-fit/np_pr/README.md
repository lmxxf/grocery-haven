---
license: other
license_name: mixed
license_link: https://huggingface.co/neuronpedia/jacobian-lens#license
tags:
- jacobian_lens
- jpp_lens
- r_lens
- interpretability
---
This folder contains pre-fitted Jacobian Lenses, J++ Lenses and R-Lenses for specific models.

Jacobian Lens and J++ Lens can be explored on Neuronpedia at [https://neuronpedia.org/jlens](https://neuronpedia.org/jlens).

Some lenses were fitted by other people. Each of those has a `CREDIT.md` beside it that names the author and links to the source files.

## Jacobian Lens

The Jacobian Lenses (`<model>/jlens/`) were trained using Anthropic's [Jacobian Lens](https://github.com/anthropics/jacobian-lens) library. The same library can be used to load the lens and local visualizer.

Neuronpedia fitted the lenses marked "Neuronpedia". Each fit reads up to 1,000 prompts of [Salesforce/wikitext](https://huggingface.co/datasets/Salesforce/wikitext) (`wikitext-103-raw-v1`), 128 tokens each, and stops when the maps stop changing. "Prompts" is the number of prompts the fit used.

Other people fitted the lenses marked with their names. We did not change their maps, but we cast some of them from fp32 to fp16. Each `CREDIT.md` gives the changes.

| Model | File | Fitted by | Prompts |
|---|---|---|---|
| [deepseek-ai/DeepSeek-V4-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | `deepseek-v4-flash/jlens/NeelNanda-pile-10k/deepseek-v4-flash_jacobian_lens_cblank.pt` | [Camila Blank](https://huggingface.co/camilablank) | 25 |
| [Poseidon-Research/Dolos-1.5B](https://huggingface.co/Poseidon-Research/Dolos-1.5B) | `dolos-1.5b/jlens/Salesforce-wikitext/Dolos-1.5B_jacobian_lens.pt` | bubskee (Team Iron Golem) | 64 |
| [google/gemma-2-27b](https://huggingface.co/google/gemma-2-27b) | `gemma-2-27b/jlens/Salesforce-wikitext/gemma-2-27b_jacobian_lens.pt` | Neuronpedia | 780 |
| [google/gemma-2-2b](https://huggingface.co/google/gemma-2-2b) | `gemma-2-2b/jlens/Salesforce-wikitext/gemma-2-2b_jacobian_lens.pt` | Neuronpedia | 454 |
| [google/gemma-2-2b-it](https://huggingface.co/google/gemma-2-2b-it) | `gemma-2-2b-it/jlens/Salesforce-wikitext/gemma-2-2b-it_jacobian_lens.pt` | Neuronpedia | 337 |
| [google/gemma-2-9b](https://huggingface.co/google/gemma-2-9b) | `gemma-2-9b/jlens/Salesforce-wikitext/gemma-2-9b_jacobian_lens.pt` | Neuronpedia | 462 |
| [google/gemma-2-9b-it](https://huggingface.co/google/gemma-2-9b-it) | `gemma-2-9b-it/jlens/Salesforce-wikitext/gemma-2-9b-it_jacobian_lens.pt` | Neuronpedia | 453 |
| [google/gemma-3-12b-pt](https://huggingface.co/google/gemma-3-12b-pt) | `gemma-3-12b/jlens/Salesforce-wikitext/gemma-3-12b-pt_jacobian_lens.pt` | Neuronpedia | 775 |
| [google/gemma-3-12b-it](https://huggingface.co/google/gemma-3-12b-it) | `gemma-3-12b-it/jlens/Salesforce-wikitext/gemma-3-12b-it_jacobian_lens.pt` | Neuronpedia | 844 |
| [google/gemma-3-1b-pt](https://huggingface.co/google/gemma-3-1b-pt) | `gemma-3-1b/jlens/Salesforce-wikitext/gemma-3-1b-pt_jacobian_lens.pt` | Neuronpedia | 467 |
| [google/gemma-3-1b-it](https://huggingface.co/google/gemma-3-1b-it) | `gemma-3-1b-it/jlens/Salesforce-wikitext/gemma-3-1b-it_jacobian_lens.pt` | Neuronpedia | 460 |
| [google/gemma-3-270m](https://huggingface.co/google/gemma-3-270m) | `gemma-3-270m/jlens/Salesforce-wikitext/gemma-3-270m_jacobian_lens.pt` | Neuronpedia | 302 |
| [google/gemma-3-270m-it](https://huggingface.co/google/gemma-3-270m-it) | `gemma-3-270m-it/jlens/Salesforce-wikitext/gemma-3-270m-it_jacobian_lens.pt` | Neuronpedia | 278 |
| [google/gemma-3-27b-pt](https://huggingface.co/google/gemma-3-27b-pt) | `gemma-3-27b/jlens/Salesforce-wikitext/gemma-3-27b-pt_jacobian_lens.pt` | Neuronpedia | 670 |
| [google/gemma-3-27b-it](https://huggingface.co/google/gemma-3-27b-it) | `gemma-3-27b-it/jlens/Salesforce-wikitext/gemma-3-27b-it_jacobian_lens.pt` | Neuronpedia | 828 |
| [google/gemma-3-4b-pt](https://huggingface.co/google/gemma-3-4b-pt) | `gemma-3-4b/jlens/Salesforce-wikitext/gemma-3-4b-pt_jacobian_lens.pt` | Neuronpedia | 616 |
| [google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) | `gemma-3-4b-it/jlens/Salesforce-wikitext/gemma-3-4b-it_jacobian_lens.pt` | Neuronpedia | 546 |
| [google/gemma-4-31B](https://huggingface.co/google/gemma-4-31B) | `gemma-4-31b/jlens/Salesforce-wikitext/gemma-4-31B_jacobian_lens.pt` | Neuronpedia | 861 |
| [google/gemma-4-E2B](https://huggingface.co/google/gemma-4-E2B) | `gemma-4-e2b/jlens/Salesforce-wikitext/gemma-4-E2B_jacobian_lens.pt` | Neuronpedia | 455 |
| [google/gemma-4-E4B](https://huggingface.co/google/gemma-4-E4B) | `gemma-4-e4b/jlens/Salesforce-wikitext/gemma-4-E4B_jacobian_lens.pt` | Neuronpedia | 663 |
| [openai/gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | `gpt-oss-20b/jlens/Salesforce-wikitext/gpt-oss-20b_jacobian_lens.pt` | Neuronpedia | 457 |
| [openai-community/gpt2](https://huggingface.co/openai-community/gpt2) | `gpt2-small/jlens/Salesforce-wikitext/gpt2_jacobian_lens.pt` | Neuronpedia | 277 |
| [meta-llama/Llama-3.1-8B](https://huggingface.co/meta-llama/Llama-3.1-8B) | `llama3.1-8b/jlens/Salesforce-wikitext/Llama-3.1-8B_jacobian_lens.pt` | Neuronpedia | 539 |
| [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | `llama3.1-8b-it/jlens/Salesforce-wikitext/Llama-3.1-8B-Instruct_jacobian_lens.pt` | Neuronpedia | 461 |
| [meta-llama/Llama-3.3-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) | `llama3.3-70b-it/jlens/Salesforce-wikitext/Llama-3.3-70B-Instruct_jacobian_lens.pt` | Neuronpedia | 125 |
| [allenai/Olmo-3-1025-7B](https://huggingface.co/allenai/Olmo-3-1025-7B) | `olmo-3-1025-7b/jlens/Salesforce-wikitext/Olmo-3-1025-7B_jacobian_lens.pt` | Neuronpedia | 568 |
| [allenai/Olmo-3-1125-32B](https://huggingface.co/allenai/Olmo-3-1125-32B) | `olmo-3-1125-32b/jlens/Salesforce-wikitext/Olmo-3-1125-32B_jacobian_lens.pt` | Neuronpedia | 456 |
| [EleutherAI/pythia-70m-deduped](https://huggingface.co/EleutherAI/pythia-70m-deduped) | `pythia-70m-deduped/jlens/Salesforce-wikitext/pythia-70m-deduped_jacobian_lens.pt` | Neuronpedia | 1,000 |
| [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | `qwen2.5-1.5b-it/jlens/Salesforce-wikitext/Qwen2.5-1.5B-Instruct_jacobian_lens.pt` | bubskee (Team Iron Golem) | 64 |
| [Qwen/Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | `qwen2.5-7b-it/jlens/Salesforce-wikitext/Qwen2.5-7B-Instruct_jacobian_lens.pt` | Neuronpedia | 485 |
| [Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B) | `qwen3-1.7b/jlens/Salesforce-wikitext/Qwen3-1.7B_jacobian_lens.pt` | Neuronpedia | 466 |
| [Qwen/Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B) | `qwen3-14b/jlens/NeelNanda-pile-10k/Qwen3-14B_jacobian_lens.pt` | bubskee | 25 |
| [Qwen/Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B) | `qwen3-14b/jlens/Salesforce-wikitext/Qwen3-14B_jacobian_lens.pt` | Neuronpedia | 615 |
| [Qwen/Qwen3-32B](https://huggingface.co/Qwen/Qwen3-32B) | `qwen3-32b/jlens/Salesforce-wikitext/Qwen3-32B_jacobian_lens.pt` | Neuronpedia | 557 |
| [Qwen/Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | `qwen3-4b/jlens/Salesforce-wikitext/Qwen3-4B_jacobian_lens.pt` | Neuronpedia | 479 |
| [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) | `qwen3-8b/jlens/Salesforce-wikitext/Qwen3-8B_jacobian_lens.pt` | Neuronpedia | 461 |
| [Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B) | `qwen3.5-0.8b/jlens/Salesforce-wikitext/Qwen3.5-0.8B_jacobian_lens.pt` | Neuronpedia | 233 |
| [Qwen/Qwen3.5-27B](https://huggingface.co/Qwen/Qwen3.5-27B) | `qwen3.5-27b/jlens/Salesforce-wikitext/Qwen3.5-27B_jacobian_lens.pt` | Neuronpedia | 672 |
| [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) | `qwen3.5-2b/jlens/Salesforce-wikitext/Qwen3.5-2B_jacobian_lens.pt` | Neuronpedia | 283 |
| [Qwen/Qwen3.5-2B-Base](https://huggingface.co/Qwen/Qwen3.5-2B-Base) | `qwen3.5-2b-pt/jlens/Salesforce-wikitext/Qwen3.5-2B-Base_jacobian_lens.pt` | Neuronpedia | 335 |
| [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | `qwen3.5-4b/jlens/Salesforce-wikitext/Qwen3.5-4B_jacobian_lens.pt` | Neuronpedia | 417 |
| [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | `qwen3.5-4b/jlens/Salesforce-wikitext/Qwen3.5-4B_jacobian_lens_n1000.pt` | Mateusz Piotrowski (@mntss) | 1,000 |
| [Qwen/Qwen3.5-9B-Base](https://huggingface.co/Qwen/Qwen3.5-9B-Base) | `qwen3.5-9b-pt/jlens/Salesforce-wikitext/Qwen3.5-9B-Base_jacobian_lens.pt` | Neuronpedia | 458 |
| [Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) | `qwen3.6-27b/jlens/Salesforce-wikitext/Qwen3.6-27B_jacobian_lens_n1000.pt` | Mateusz Piotrowski (@mntss) | 1,000 |
| [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | `qwen3.8-27b/jlens/bilingual-wikitext-zhwiki/Qwen3.8-27B_jacobian_lens.pt` | [Jin Yanyan](https://huggingface.co/lmxxf) | 100 |

The Qwen3-14B lens by bubskee maps to the output of block 38, and the DeepSeek-V4-Flash lens maps to the output of block 41. All other lenses map to the final block. Those two lenses were fitted on [NeelNanda/pile-10k](https://huggingface.co/datasets/NeelNanda/pile-10k).

## J++ Lens

The J++ Lenses (`<model>/jpp/`) are from *J++ Lens: Jacobian Filtering Enables More Faithful Workspace Lenses* (Ayonrinde & Lindsey, 2026). J++ Lens is an improved, drop-in replacement for the Jacobian Lens. It is more coherent on earlier layers, where the Jacobian Lens is often unreliable.

Credit for the method and for the lenses marked "Ayonrinde & Lindsey" goes to the authors. Their original lens files are at [koayon/jpp-lenses](https://huggingface.co/koayon/jpp-lenses). We changed those files to the format that the Neuronpedia inference server and the Jacobian Lens files use. We cast the maps from fp32 to fp16 (relative error 2.7e-4 or less; 1.1e-3 for Gemma 4 31B, which has very small values in some layers). We did not change them in other ways. We fitted the lenses marked "Neuronpedia" with the paper's code and recipe. [bubskee](https://huggingface.co/bubskee) fitted the lenses marked "bubskee" with the paper's code, and we converted them in the same way.

| Model | File | Fitted by | Recall@10 |
|---|---|---|---|
| [Qwen/Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) | `qwen3.6-27b/jpp/Salesforce-wikitext/Qwen3.6-27B_jpp_lens.pt` | Ayonrinde & Lindsey | 55.2% |
| [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | `qwen3.5-9b/jpp/Salesforce-wikitext/Qwen3.5-9B_jpp_lens.pt` | Ayonrinde & Lindsey | 55.0% |
| [google/gemma-4-31B](https://huggingface.co/google/gemma-4-31B) | `gemma-4-31b/jpp/Salesforce-wikitext/gemma-4-31B_jpp_lens.pt` | Ayonrinde & Lindsey | 58%* |
| [allenai/Olmo-3-1125-32B](https://huggingface.co/allenai/Olmo-3-1125-32B) | `olmo-3-1125-32b/jpp/Salesforce-wikitext/Olmo-3-1125-32B_jpp_lens.pt` | Ayonrinde & Lindsey | 50.0% |
| [Qwen/Qwen3.5-122B-A10B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B) | `qwen3.5-122b-a10b/jpp/Salesforce-wikitext/Qwen3.5-122B-A10B_jpp_lens.pt` | Ayonrinde & Lindsey | 48.4% |
| [deepseek-ai/DeepSeek-V4-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) | `deepseek-v4-flash/jpp/Salesforce-wikitext/DeepSeek-V4-Flash_jpp_lens.pt` | Ayonrinde & Lindsey | 61.4% |
| [Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B) | `qwen3.5-0.8b/jpp/Salesforce-wikitext/Qwen3.5-0.8B_jpp_lens.pt` | Neuronpedia | 44.9% |
| [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) | `qwen3.5-2b/jpp/Salesforce-wikitext/Qwen3.5-2B_jpp_lens.pt` | Neuronpedia | 51.5% |
| [Qwen/Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) | `qwen3-4b/jpp/Salesforce-wikitext/Qwen3-4B_jpp_lens.pt` | Neuronpedia | 53.8% |
| [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | `llama3.1-8b-it/jpp/Salesforce-wikitext/Llama-3.1-8B-Instruct_jpp_lens.pt` | bubskee | 52.7%† |
| [google/gemma-3-12b-pt](https://huggingface.co/google/gemma-3-12b-pt) | `gemma-3-12b/jpp/Salesforce-wikitext/gemma-3-12b-pt_jpp_lens.pt` | bubskee | 61.1%*† |
| [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | `qwen3.5-4b/jpp/Salesforce-wikitext/Qwen3.5-4B_jpp_lens.pt` | bubskee | 57.2%† |
| [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | `qwen2.5-1.5b-it/jpp/Salesforce-wikitext/Qwen2.5-1.5B-Instruct_jpp_lens.pt` | bubskee (Team Iron Golem) | 51.5%† |
| [Poseidon-Research/Dolos-1.5B](https://huggingface.co/Poseidon-Research/Dolos-1.5B) | `dolos-1.5b/jpp/Salesforce-wikitext/Dolos-1.5B_jpp_lens.pt` | bubskee (Team Iron Golem) | 52.1%† |

Recall@10 is macro recall on the paper's labelled readout items. The scores for the "Ayonrinde & Lindsey" lenses are from [koayon/jpp-lenses](https://huggingface.co/koayon/jpp-lenses). We scored the "Neuronpedia" lenses with the paper's evaluation, on its held-out items.

\*The poetry task is dropped for Gemma 4 31B, where only 1 of its 98 items passes the correctness filter. It is also dropped for Gemma 3 12B.

†Reported by bubskee in the source repository, with the paper's evaluation. We did not run these scores again. See each `CREDIT.md` for the source.

## R-Lens

The R-Lenses (`<model>/rlens/`) are from *R-lens: Making J-lens More Faithful on Early Layers* (Camila Blank, Agam Bhatia and Neel Nanda, 2026). An R-Lens is a Jacobian Lens fitted with a modified backward pass. It uses the same file format. [bubskee](https://huggingface.co/bubskee) fitted all of them.

| Model | File | Fitted by |
|---|---|---|
| [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | `llama3.1-8b-it/rlens/Salesforce-wikitext/Llama-3.1-8B-Instruct_rlens.pt` | bubskee |
| [google/gemma-3-12b-pt](https://huggingface.co/google/gemma-3-12b-pt) | `gemma-3-12b/rlens/Salesforce-wikitext/gemma-3-12b-pt_rlens.pt` | bubskee |
| [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | `qwen3.5-4b/rlens/Salesforce-wikitext/Qwen3.5-4B_rlens.pt` | bubskee |
| [Qwen/Qwen3-14B](https://huggingface.co/Qwen/Qwen3-14B) | `qwen3-14b/rlens/NeelNanda-pile-10k/Qwen3-14B_rlens.pt` | bubskee |
| [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | `qwen2.5-1.5b-it/rlens/Salesforce-wikitext/Qwen2.5-1.5B-Instruct_rlens.pt` | bubskee (Team Iron Golem) |
| [Poseidon-Research/Dolos-1.5B](https://huggingface.co/Poseidon-Research/Dolos-1.5B) | `dolos-1.5b/rlens/Salesforce-wikitext/Dolos-1.5B_rlens.pt` | bubskee (Team Iron Golem) |

## File format

Each `.pt` lens file is a `torch.save` dictionary, loadable with `torch.load(path, weights_only=True)`:

| Key | Value |
|---|---|
| `J` | `{layer: fp16 Tensor[d_model, d_model]}`, the map from that layer's residual stream to the target layer's (the final block, unless `provenance` states a `target_layer`) |
| `source_layers` | the layers in `J`: every block before the target layer |
| `d_model` | the residual width |
| `n_prompts` | the number of prompts in the fit |
| `provenance` | the source file, the method, the fitting configuration, and the activation that the maps read (`capture_point`, `stream_reduce`) |

The readout at layer ℓ for a residual `h` is `logits = unembed(h @ J[ℓ].T)`, where `unembed` is the model's final norm followed by its LM head. For DeepSeek-V4-Flash, `h` is the mean of the four residual streams.

The `config.yaml` beside each file records the source, the fitting configuration, and the command that wrote the file.

## License

Each lens is derived from its base model. The base model's license applies to the lens files in that model's folder:

| Folders | License |
|---|---|
| `llama3.1-8b/`, `llama3.1-8b-it/` | [Llama 3.1 Community License](https://www.llama.com/llama3_1/license/) and its Acceptable Use Policy. See `LICENSE`, `USE_POLICY.md` and `NOTICE` in each folder. Built with Llama. |
| `llama3.3-70b-it/` | [Llama 3.3 Community License](https://www.llama.com/llama3_3/license/) and its Acceptable Use Policy. See `LICENSE`, `USE_POLICY.md` and `NOTICE` in the folder. Built with Llama. |
| `gemma-2-*/`, `gemma-3-*/` | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) and the [Gemma Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy). See `NOTICE` in each folder. |
| `deepseek-v4-flash/jlens/` | MIT, as the source repository states. |
| All other folders | Apache-2.0. |

The `oracle/` folders also have their own `LICENSE` and `CREDITS.md`.

The J++ Lens files fitted by Ayonrinde & Lindsey are Apache-2.0 in the source repository. The J++ Lens method builds on the Jacobian Lens of Gurnee et al. (2026) and the R-Lens of Camila Blank, Agam Bhatia and Neel Nanda.

## Citation

Citation information for the J++ Lens paper is coming soon.
