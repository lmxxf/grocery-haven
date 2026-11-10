# 第 365 期实验任务单：双机 DGX Spark 训练 Qwen3.8-27B 专属 Jacobian Lens (J-lens)

**派单人**：鳩（主脑）  
**执行人**：闇（工程主力，`wM:p1`）  
**执行机器**：家里双机 DGX Spark（主机 `spark-3a10`: `192.168.31.198` / CX7 `169.254.248.35`；从机 `spark-slave`: CX7 `169.254.30.81`）。**⚠️ 严禁在本机 RTX 3080 Laptop 上跑任何 GPU 任务！**

---

## 一、 铁律与内存安全硬护栏（防 Spark 死机，最高优先级）

1. **模型加载方式（严禁直接 `AutoModelForCausalLM.from_pretrained` 加载 27B）**：
   - 必须复用主机 `/home/lmxxf/work/interp-curvature-exp/run_curvature_experiments.py` 里的 `load_model('Qwen3.8-27B-FP8')` 流式加载方案：
     - `with torch.device('meta'): model = Qwen3_5ForCausalLM(cfg)`
     - 逐个 shard 使用 `safe_open(..., framework='pt', device='cuda')` 读取，将 128×128 FP8 block 原地反量化为 `bfloat16`，每个 shard 读完立刻 `drop_caches`（`gc.collect(); torch.cuda.empty_cache(); sudo -n sh -c 'echo 3 > /proc/sys/vm/drop_caches'`）；
     - 手动初始化 `model.model.rotary_emb = Qwen3_5TextRotaryEmbedding(cfg).to('cuda')`。
   - 加载完成后，BF16 权重常驻约 **50.1 GiB**，单机剩余可用内存 > **60 GiB**。

2. **三道内存熔断**：
   - 启动前检查 `/proc/meminfo` 的 `MemAvailable > 100 GiB`（不够先 drop_caches）；
   - 进程内后台守护线程每 0.25s 检查 `MemAvailable`，一旦 `< 22 GiB` 立即打印告警并 `os._exit(73)`；
   - 外部独立监控看门狗：如果 `MemAvailable < 20 GiB` 立即 kill 整个模型进程组。

3. **双机数据并行（利用 `JacobianLens.merge`）**：
   - 先从主机 `spark-3a10` 通过 CX7 高速网口（`169.254.30.81`，速度 600+ MB/s）将 `/home/lmxxf/work/models/Qwen3.8-27B-FP8` rsync 同步到 `spark-slave:/home/lmxxf/work/models/Qwen3.8-27B-FP8`（同步前先查一下 `spark-slave` 的 `df -h` 确保磁盘够 28GB）；
   - 主从两台机器各自独立加载一份 `Qwen3.8-27B`，主机跑偶数编号语料（`0, 2, 4, ..., 98`，共 50 条），从机跑奇数编号语料（`1, 3, 5, ..., 99`，共 50 条），最后把从机的 checkpoint 拉回主机，用 `jlens.JacobianLens.merge()` 合并！

---

## 二、 具体执行步骤

### Step 1：环境与官方 `jlens` 库部署
- 在 `spark-3a10:/home/lmxxf/work/jlens-qwen38-27b/` 建立实验工作目录，克隆 Anthropic 官方仓库 `https://github.com/anthropics/jacobian-lens.git` 并 `pip install -e .`（或直接在脚本里 `sys.path.insert` 引用 `jlens`），同步到 `spark-slave:/home/lmxxf/work/jlens-qwen38-27b/`。
- **注意 `Qwen3_5ForCausalLM` 与 `jlens.from_hf` 的适配**：
  - 我们的流式加载器返回的是 `Qwen3_5ForCausalLM` 实例（其内部结构为 `model.model.layers`、`model.model.norm`、`model.model.embed_tokens`、`model.lm_head`），`jlens.from_hf(hf_model, tok, force_bos=False)` 默认的 `Layout("model")` 可以直接匹配；
  - 检查 `tok` 对输入文本的编码长度，确保每条语料 tokenize 后长度 $\ge 128$ tokens（使 `max_seq_len=128` 截断后恰好是 128 tokens，`valid_position_mask(128, skip_first=16)` 有 111 个有效位置）。

### Step 2：准备 100 条高代表性中英双语预训练风格语料 (`prompts_100.json`)
- 构造 100 条长自然段落（每条 tokenize 后 $\ge 160$ tokens，拟合时截断为 `max_seq_len=128`）：
  - **50 条英文段落**：从 HuggingFace `Salesforce/wikitext` (`wikitext-103-raw-v1`) 或官方 `jlens` 数据/百科长文中抽取 50 条不同领域的英文百科段落；
  - **50 条中文段落**：从中文百科/历史/科学/散文长文本中抽取 50 条高质量中文长段落（严禁混入短句或指令模板，保持纯正预训练文本分布）；
  - **中英交错排列**：`idx = 0, 2, 4...` 为英文，`idx = 1, 3, 5...` 为中文，确保任意前缀子集都是 1:1 中英均衡。

### Step 3：在 `spark-3a10` 上跑 1 条语料 Smoke Test（校准耗时与 `dim_batch`）
- 先在主机上加载模型，对 `prompts_100[0]` 跑 1 条 `jacobian_for_prompt`：
  - 先对比测试 `dim_batch = 8` 和 `dim_batch = 16`（在 `max_seq_len = 128`、全 63 个 `source_layers = list(range(63))`、`target_layer = 63` 下）的单条耗时、峰值 CUDA 内存与最低 `MemAvailable`；
  - 选定既绝对安全（最低 `MemAvailable > 45 GiB`）又最快的 `dim_batch` 参数。
  - **如果全 63 层 × 100 条在双机上耗时超过 35 分钟**，可以根据实测单条耗时动态决定：要么双机跑满 60～100 条全 63 层，要么密集覆盖关键层，但优先争取 **全 63 层（0..62）** 完整拟合（若单条 30 秒，双机各跑 30～50 条也就 15～25 分钟！）。

### Step 4：双机并行拟合与多阶段收敛快照保存
- 主机 `spark-3a10` 与从机 `spark-slave` 同时启动拟合进程；
- 每处理完一条语料，记录日志指标：`prompt_idx`, `lang`, `elapsed_sec`, `min_avail_GiB`, `prompt_norm` ($\max_\ell \|J_\ell\|_F / \sqrt{d}$), 以及相对均值变化率 `mean_rel_change`；
- 在双机合计完成 **$N = 1, 2, 4, 10, 20, 50, 100$**（若跑 60 条则是 $1, 2, 4, 10, 20, 40, 60$）个样本节点时，导出合并后的 `JacobianLens` 快照（保存 `n1`, `n2`, `n10`, `n20`, `n50`, `n100` 的镜头或它们在评测题上的完整读数，最终满血版镜头保存为 `Qwen3.8-27B_jacobian_lens.pt`）。

### Step 5：第一期公众号核心实验分析与评测报告
利用训好的各阶段镜头，跑完以下三组分析并把结果数据 JSON、图表和 `实验报告.md` 同步回本机 `/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-365-jlens-fit/`：
1. **收敛动力学与镜头结构解剖**：
   - 绘制并统计随着语料条数 $N$ 从 1 增加到最终条数时，`mean_rel_change` 的 $1/N$ 收敛曲线，以及不同 $N$ 之间镜头矩阵的余弦相似度；
   - 统计全 63 层每一层的雅可比矩阵范数 $\|J_\ell\|_F / \sqrt{d}$、对角线占比（Diagonal Dominance，衡量离恒等映射有多远，解释为什么浅中层 Logit Lens 失效而 J-lens 有效），并对比 `Qwen3.8-27B` 独特的 **`linear_attention`（每4层前3层） vs `full_attention`（每4层第4层）** 在雅可比矩阵谱/范数上的周期性纹理！
2. **“镜头去雾过程”实测对比（Logit Lens vs $N=1$ vs $N=10$ vs $N=50$ vs $N_{\text{final}}$）**：
   - 在 8 道中英文代表性测试题上（包含官方 `ascii-face`、英文两跳 `Fact: The currency used in the country shaped like a boot is`、中文两跳 `常识：形状像一只靴子的欧洲国家使用的法定货币是`、`猜谜：会结网捕食飞虫、长有八条腿的节肢动物是`、`中国的首都是北京，那么与法国接壤、首都位于马德里的国家是` 等），提取从浅层到深层（0..63 层）的 Top-5 词汇排行榜与目标中间概念（如 `nose`、`Italy`/`意大利`、`spider`/`蜘蛛`、`Spain`/`西班牙`）的 Rank 轨迹！
3. **官方基准定量跑分（Lens Quality Eval）**：
   - 在 Anthropic 官方仓库的 `data/evaluations/lens-eval-multihop.json` 和 `lens-eval-multilingual.json`（或 `lens-eval-association.json`）上，对比 Vanilla Logit Lens (`use_jacobian=False`) 与我们训出的不同 $N$ 阶段 J-lens 的 `pass@1`, `pass@5`, `pass@10` 命中率！

---

请读取本任务单后立即开始执行，完成全部实验与本地同步后汇报结果！
