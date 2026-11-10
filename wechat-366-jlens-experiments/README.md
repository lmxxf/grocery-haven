# 366：J-lens 四组前向/干预实验（已完成）

请先读 `实验报告.md`。所有模型与GPU操作只在Spark主机运行，本机只整理、画图和CPU验证。远端目录 `/home/lmxxf/work/jlens-366-experiments/`。

- `results.json`：结果索引、统计和边界；`validation.json`：验收、文件哈希；`provenance.json`：模型、镜头和代码身份。
- `experiment1.json`：9格式、68个原始token位置、64层、Vanilla/N1/N100，合计13056个位置读数；两位数使用明确的00..99条件序列排名。
- `experiment2.json`：6题、三种语义方向与逐位置范数匹配随机、三个剂量；`experiment2_annotated.json`：保留原结果，另外以首个回答段重评分。
- `experiment3.json`：单层单位置固定预设增量的三路广播，以及法语续写/问语种对照。
- `experiment4.json`：3概念×3剂量、随机以及N1/Vanilla面包校准对照；基线也保留。
- `experiment4_dosecheck.json`：hook生效检查与有限的面包强剂量补测。
- `arithmetic_position_check.json`：根据实验1的L55+峰值追加的探索性数字6→4定位，不把它冒充独立验证。
- `concept_directions.pt`：按需词元方向，包含最终Norm权重的对齐；没有物化整个词表大字典。

## 白底SVG

`arithmetic_token_heatmap.svg`、`arithmetic_formats.svg`、`swap_effects.svg`、`broadcast_effects.svg`、`introspection_results.svg`。

## 复现入口

Spark既有venv：`/home/lmxxf/work/interp-curvature-exp/venv/bin/python`。`pipeline.py supervise`按1→4执行；保留逐shard流式加载、22GiB进程内熔断和20GiB父进程看门狗。`pipeline.py supervise supplement`、`pipeline.py supervise arithmetic_check`是两个有明确边界的补核验入口。镜头和原模型复用365目录，无需复制或改动权重。

本次生成不是无限长度完整会话：主任务以固定32/48 tokens观察首答，内省128 tokens，原文、token IDs和hit_limit都保留。单次greedy、少量问题的题数比例不是部署成功概率。方向可读、方向干预有效、受试自我报告是三件事，不相互替代。
