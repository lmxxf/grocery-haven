# 关系前缀实验复现

全部推理在 Spark GB10 执行。本地只接收结果并阅读文件。

Spark 工作目录：`/home/lmxxf/work/interp-curvature-exp/relation_tags/`。
环境沿用上级 `venv/`，模型沿用 `/home/lmxxf/work/models/`。

运行流程（依次执行，单模型驻留）：

```bash
cd /home/lmxxf/work/interp-curvature-exp/relation_tags
../venv/bin/python run_relation_tags.py --model Qwen3.5-35B-A3B-Base
../venv/bin/python run_relation_tags.py --model Qwen3-0.6B
../venv/bin/python run_relation_tags.py --model Qwen3.5-35B-A3B
../venv/bin/python export_review.py
```

人工按 scoring_rubric.md 逐一核查 blind_review.json，将去重答案的判分写入 grades.json。相同问题/相同回答共享同一判分；答复本身可能包含称呼，不宣称真正双盲。既有 raw/ 文件会跳过；重新生成必须另建干净输出目录或明确移走既有文件。

```bash
../venv/bin/python analyze.py
../venv/bin/python plot.py
```

`results.json` 为全部输入、完整生成、首轮边界、指标与判分；`raw.tar.gz` 是全部逐层/逐词元测量及环境配置。`transcripts.md` 为完整原话。继承的原始测量及加载代码备份在 dependencies/；恢复复现时将其放回上级和上级 basepost/ 对应路径。

熵来自完整词表，不使用 top-k 截断。生成贪心、上限160；首轮解析不影响模型继续生成。曲率来自固定生成序列无缓存重放，缓存/重放不一致率另审计；它并非每步缓存推理隐藏状态的精确记录。所有因果解释限于固定示例和标签对，不能单独隔离 Mother 与 I 各自贡献。
