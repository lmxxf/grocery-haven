# Qwen3.8-27B：全64层双语 ICA-Lens

最终结果入口：`实验报告.md`、`summary.json`。**以 `final_acceptance.json` 的 PASS 为工程收尾依据；仅有某层 complete.json 不代表其词表、补测和同步已完成。**

- `validation.json`：原产物全张量有限性、配置、逐轴κ计数、原142探针坐标重算与32行C·M抽查。
- `posthoc_validation.json`、`source_sha256*.json`：从机→主机→本机SHA256对照、72条多义词探针与词表验收。
- `polysemy_summary.json`：bank/苹果跨层对比，8例/义选轴与4例/义留出，不能把64层重复预测当独立样本。
- `steering_full_text.md`：六代表层48条完整原话（12 baseline、36干预）。
- `Lxx/native/`：官方icalens格式；`Lxx/oriented.safetensors`：fit-skew朝向后的reading/mixing/center，原组件ID不变。
- `Lxx/statistics.json`：fit/heldout峰度、偏度、全轴Top5激活索引、原探针得分。
- `Lxx/contexts_decoded.json`：一次解码整个因果左文切片；优先用它，不用早期逐token拼接的contexts.json判断中文。
- `Lxx/vocabulary_readouts.json`、`Lxx/polysemy_readouts.json`：Vanilla / N100 J-lens Top20，后者附正负两个方向。
- `Lxx/saelens_adapter.*`：需要外部row-L2的正半波ReLU兼容权重，不等于有符号ICA本体。

每层5120成分，全64层是327680个“层-成分对”，不是一个327680宽的单层字典。L0指第0个block输出，不是embedding；L63为最后block输出。

## 运行位置与复跑

模型前向、拟合、干预脚本只在DGX Spark运行；本机仅做CPU验证、汇总和作图。

远端两机工作目录均为 `/home/lmxxf/work/ica-lens-qwen38-27b/`，Python为 `/home/lmxxf/work/interp-curvature-exp/venv/bin/python`。`controller.py main/slave` 的分工与三道内存检查见上级 `experiment_design.md`。核心依赖采用上级 `icalens_pkg/icalens/` 0.4.0源码，远端放在工作目录的 `icalens_pkg/`，未降级现有transformers。

`worker.py extract` 复用 `loader_reference.py` 的逐shard FP8→BF16加载。每阶段提取后退出模型，再逐层 `worker.py fit`、`analyze.py readout`；仅首批代表层另做 `analyze.py steer`。大激活按既定策略在读出完成后释放；保留了语料、探针残差、透镜和全部统计，完整自然语料四阶矩复算需要重新提取。

`collect_polysemy.py` / `posthoc_polysemy.py` / `extra_readouts.py` 在原拟合完全结束后做中央补测；`run_guarded.py` 为独立20GiB进程组看门狗，worker另有22GiB内部守护。原始N100 J-lens本机归档位于相邻 `wechat-365-jlens-fit/lens_n100.pt`，远端以同名文件/链接引用，SHA见input_audit.json。

CPU收尾顺序：`validate_products.py` → `validate_posthoc.py` → `summarize.py` → `make_figures.py` → `final_accept.py`。所有代码和结果保留失败、无变化与混合方向；高κ计数不充当人工语义轴总数。
