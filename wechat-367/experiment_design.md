# Qwen3.8-27B 双语 ICA-Lens：执行设计

2026-11-10；脚本位于 experiment/，远端两机 /home/lmxxf/work/ica-lens-qwen38-27b/。本机只做文件处理，不调用 CUDA。

## 固定设置与双机分工

- 64 个 Transformer block 输出，L0..L63，d=5120；不是 embedding 加 64 层的 hidden_states 索引。
- 官方 icalens 0.4.0 未改数学核心；parallel/symmetric FastICA，logcosh，完整5120成分，固定50迭代，seed367，row_normalize=True，batch8192；每5步记录 contrast 分位数。固定迭代不等于已证明收敛。
- 拟合 FP32，torch matmul precision=high；官方协方差 FP64累加。运行现有验证环境，不按包依赖降级 transformers。
- 拟合200704 tokens，留出51200 tokens；每部分严格中英文各半。WikiText-103 与20231101中文维基；按文档隔离训练/留出，长度≥128，窗口≤512，一篇最多4096 tokens。语料SHA见 corpus_manifest.json，两机完全相同。
- 主机先L0/38/56，从机先L16/41/63。其余层升序交错分配，每机共32层；不将不同语言分到不同层。

## 内存与磁盘

复用 loader_reference.py：meta构建+逐shard FP8 128×128块原地反量化BF16，逐shard清缓存，重建rotary。禁止27B普通from_pretrained。启动子进程前清page cache并要求MemAvailable≥100GiB；内部每0.25秒低于22GiB退出；独立controller每0.25秒低于20GiB杀子进程组。

先加载模型提取一个阶段的层激活，退出整个进程，才启动各层ICA拟合。每层FP32磁盘约4.80GiB（两split），首批3层约14.4GiB，后批29层约139.3GiB/机；写入逐窗口flush和madvise。确认剩余空间超过需求+10GiB。每层完成读出后才删自产激活；原始模型与其他实验文件不动。原生透镜、统计、上下文、探针、读出、生成均保留。

## 统计与概念读出

保存native artifact（原官方组件编号）、oriented.safetensors（components/mixing/center/fit-skew符号）、fit与heldout的skewness/excess kurtosis。κ=E[(Y−μ)^4]/Var(Y)^2−3；主计数使用独立留出κ>1/>10。符号同时翻reading行与mixing列，编号保持官方contrast排序，不偷换成κ排序。

全轴保存最高激活5个留出token及索引；挑κ最高96与语言差最高8轴导出左侧64token上下文（不含未来）。这是候选筛查，不能把高κ数量直接写成“语义清晰概念数量”。

64组中英平行句（48拟合/16留出，主体分开）末尾统一添加同一个换行词元，避免句号/中文句号混淆。Δ=mean(Y_zh−Y_en)；按拟合选择，留出验证方向。另有bank、apple与苹果的14条因果前缀探针，目标词之前的上下文提供词义，非向未来偷看。这些小样本只支持探索性分析。

候选轴writing方向分别经Vanilla或N100 J_l映射，再经实际Qwen Final RMSNorm（1+weight，eps=1e-6）与lm_head，保存Top20。L63用恒等映射。词表读出只说明方向相似，不能代替因果验证。

SAELens adapter为正半波ReLU、单位decoder，并明确外部先行row-L2预处理；不是原始残差上无需预处理的SAE，不等同完整有符号ICA重构。精确有符号透镜以native/oriented权重为准。

## 优先层干预

优先层根据拟合Δ选语言轴，英文“Hangzhou is known for”与中文“杭州以什么闻名？”各做baseline、坐标±5、clamp至0；贪心生成32tokens。在prompt末位及每个生成当前末位操作单位残差，之后重新单位化、恢复原范数。故clamp=0指重新归一化之前的坐标。保存完整真实输出，不预设成功；当前属于最小因果摸底，不是论文完整ERF/SAEBench复现，也尚无随机轴大样本统计。

## 运行与验收

controller.py main/slave由nohup启动；status.json、controller.log、worker.log为当前状态。worker.py extract/fit、analyze.py readout/steer。单层complete.json只表示拟合与统计完成，整个阶段还需vocabulary_readouts.json与优先层steering.json。任务失败会显式写failed，不静默继续。全64层完成后再汇总κ分层曲线与手工验证概念；本次点火汇报不得冒充已完成拟合。
