# 曲率／熵独立复现（第361期）

报告入口：[复现报告.md](复现报告.md)。机器可读汇总：[results.json](results.json)。

所有GPU计算在 `lmxxf@192.168.31.198` 的 `/home/lmxxf/work/curvature-icml2026-361/` 执行，环境为相邻实验已用的 `/home/lmxxf/work/interp-curvature-exp/venv/`。两个官方模型存放在Spark的 `/home/lmxxf/work/models/gpt2-xl/` 与 `/home/lmxxf/work/models/pythia-2.8b/`，保留以便后续实验复用；原始权重无编辑。完整模型文件SHA与HF对象身份见 `hf_weight_identities.json` 和 `download_*.json`。

本地大数组目录：`/home/lmxxf/work/grocery-haven/curvature-icml2026-361/`。四个 `observation_*.npz` 文件包含逐层逐词元C、H、邻位熵、原篇章ID和位置。源码与观测汇总、完整扰动JSON在本目录。`raw_arrays_manifest.json` 给出本地路径、字节数和SHA-256。报告重建仅需JSON；CPU数组验证时可设置环境变量 `CURVATURE_ARRAY_ROOT` 指向grocery目录。

主要代码：

- `run_reproduction.py`：1024篇LAMBADA、512句UD补充；32个干预位置×300方向×6条件，含额外严格正交控制及直接拉直／弯曲。
- `check_suffix.py`：两种架构上验证缓存续算和完整前向等价。
- `check_layer_index.py`：只改变层号解释，检查相邻block。
- `confirm_planar.py`：一次独立128个新位置的Full／Planar确认；输入位置预先落盘，未调层与剂量。
- `run_extra.py`：常规文本、顺口溜、空间／事实题以及论文图示短提示的只读前向。
- `analyze.py`：聚合JSON、重加权边界敏感性、置信区间和SVG科学图。
- `validate_artifacts.py`：CPU数学例子、数组范围、窗口位置与代码指纹验证。

代码中的GPU入口会断言GB10，避免误在笔记本GPU跑模型。复现时先在Spark激活原环境，再按报告内顺序执行。`run_all.sh` 的等待条件是当前下载验证文件，不是一个通用模型安装器。

这是论文公式及主要控制条件对齐的独立实现，未取得作者原始样本ID或代码，不宣称逐条原始样本重放。完整差异与未完成的训练/附录实验均在报告中公开。
