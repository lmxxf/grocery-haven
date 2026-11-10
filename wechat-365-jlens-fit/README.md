# 365：Qwen3.8-27B J-lens 全矩阵实测

**已于2026-11-10完成N=100拟合、合并、全部评测、本机同步与最终验收。** `results.json` 的 `complete:true` 与 `delivery_validation.json` 的 `accepted:true` 已确认；下方保留早期运行过程说明。

- 原始任务：`task_spec.md`。
- 实时进度与口径：`实验报告.md`、`pipeline_status.json`、`results.json`。
- 已完成的单条完整镜头：`smoke_b1.pt`，63 × 5120 × 5120，官方 FP16 便携格式；`smoke_artifact_validation.json` 记录 CPU 校验。
- 远端实验目录：两台 Spark 均为 `/home/lmxxf/work/jlens-qwen38-27b/`。
- 主机日志：`fit_even.log`；从机日志：`fit_odd.log`。分别处理英文偶数索引与中文奇数索引。
- `remote_pipeline.py` 等两边各50条完成后，用官方 `JacobianLens.merge` 生成 N=1/2/4/10/20/50/100 快照，再评测官方题集与8道代表题。
- 本机 `sync_and_report.py` 是纯 CPU 的独立会话进程，定期同步 JSON 并更新进度报告；完成后同步全部快照、生成 SVG 和正式报告，再通过 herdr 通知鳩 `wK:p1`。任何流水线失败也会通知，不能伪报完成。
- 全部GPU计算只发生在两台DGX Spark，本机不运行GPU任务。

## 已知口径

矩阵计算与运行均值为完整 FP32；保存按官方默认 FP16，再加载合并包含保存舍入误差。没有低秩压缩或抽样输出维度。双语收敛必须看两边等量样本合并后的快照。1/N系数是运行均值公式的一部分，单凭更新率下降不能证明统计收敛。

普通 batch1 全矩阵预检成功，但因同时准备语料，其最低可用内存44.55 GiB，未达到45 GiB选型余量。因此正式拟合选择磁盘矩阵 batch2；生产过程两台的已观测最低可用内存分别约49 GiB和50 GiB，精确值以后续资源日志为准。

## 下午早期评测已完成

`early_evaluation_results.json` 保存 Vanilla / 正式英文N=1 / 双语N=2 的官方题集分数与代表题轨迹；`representative_top5.json` 是8道题的精简索引；`early_scores.json` 是分数表。`early_lens_quality.svg`、`early_rank_paths.svg`、`early_snapshot_change.svg` 可用于今日文章。`实验报告.md` 已收录真实提升、退化、词元语言与语义命中区别。全局N=4尚未就绪，没有等待或虚构。

## 最终交付

- `lens_n100.pt`：完整63层、5120×5120、FP16便携镜头，3,303,032,496 bytes（约3.303 GB / 3.076 GiB）；模型权重本身未改。
- `Qwen3.8-27B_jacobian_lens.pt` 是指向最终镜头的本地符号链接。
- `lens_n1/2/4/10/20/50/100.pt` 七个快照齐全。
- `evaluation_results.json`、`scores.csv`：全部八组词元读出评测；`results.json`：完整汇总。
- `convergence.svg`、`layer_structure.svg`、`lens_quality.svg`：三张最终图。
- `实验报告.md`、`delivery_validation.json`、`n100_merge_validation.json`：报告及两份验收证据。
- N=100 pass@1：多跳36.31%、多语言25.08%；这不是模型答题正确率。N50到100矩阵余弦均值0.87449，不能宣称已统计收敛。
- 双机模型计算进程与本次资源采样器均已结束，后台同步正常完成。
