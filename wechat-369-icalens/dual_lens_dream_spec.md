# 双镜合璧（ICA-Lens × N=100 J-lens）多声道解剖与梦境 SVG 自我实验规范

## 目标
单用 `J-lens` 直接投影残差流总向量 `h_l` 时，Top-5 词表往往被当前范数最大的主导信号（如标点、换行、空格或惯性算式）霸榜淹没；而先用 `ICA-Lens` 将单位化残差 `x_hat = h_l / ||h_l||_2` 横向分解为 5,120 个独立坐标 `y = (x_hat - c) @ C.T`（每根轴贡献向量为 `y_j * M[:, j]`，能量占比 `y_j^2 / sum(y^2)`），再将**激活最强或条件差分最大的单根 ICA 轴写入方向 `M[:, j]`（注意关注 `sign(y_j) * M[:, j]` 实际指向）**乘以 `J_l` 送入 `Final RMSNorm + lm_head`，即可把同一时刻并行暗涌的多条“分声道念头”逐一显影出来。

请你在 `Qwen3.8-27B-FP8`（流式 128×128 反量化 BF16，可优先在完全空闲的从机 `169.254.30.81` 提取残差向量后拉回主机，或等本机上传结束后在本机跑，挂好 `22 GiB` 内存护栏；你也可以派子代理分工）上完成以下两组实验，并将完整实测结果汇总为 `/home/lmxxf/work/ica-lens-qwen38-27b/双镜与梦境实验报告.md`（同步拷入 `/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-369-icalens/`）。

---

## 实验一：公众号硬核多声道解剖（抓出被单 J-lens 淹没的并行暗线）

对以下 3 个样本捕获全 64 层（重点细剖 `L24, L32, L38, L41, L48, L52, L55, L56, L58, L60, L63`）目标末位词元的残差向量，对比：
- **A. 整团总向量单 J-lens Top-10 词表**（`lm_head(final_norm(J_l @ h_l))`）
- **B. ICA-Lens 横向拆解 Top-10 强激活独立轴（按 `|y_j|` 及相对能量 `y_j^2` 排序）**，对每根轴用 `J_l @ (sign(y_j) * M[:, j])` 读出各自的 Top-8 词表（同时附上不乘 `J_l` 的 Vanilla Logit Lens Top-5 作对照）：

1. **空格淹没的算术中间结果（闭环 366 期）**：
   - 纯文本无 chat template：`2 * 3 + 2 =` vs 紧凑版 `2*3+2=`
   - 核查核心问题：在 `2 * 3 + 2 =` 的 `L54–L58` 中，整团 `J-lens` 里 `'6'` 被挤到了第 11 名以后；横向拆成独立 ICA 轴后，第 1 大嗓门轴在想什么（空格/格式？），**有没有哪一根前排独立 ICA 轴在乘 `J_l` 后把 `'6'` 推到了 Top-1 / Top-3？**
2. **多跳推理的“双声道同框”（闭环 365/366 期）**：
   - 纯文本无 chat template：`常识：形状像一只靴子的欧洲国家使用的法定货币是`
   - 核查核心问题：在 `L36–L58` 跳步交接区，是否能看到同一层里**一根独立 ICA 轴读出 `意大利 / Italy`**，而**另一根同时激活的独立 ICA 轴已经在读出 `欧元 / euro / 货币 / 法定`**？
3. **荒谬陷阱题的“知行断线”分声道 X 光片**：
   - Chat template（`enable_thinking=False, add_generation_prompt=True`，与 Paper 99 `render_chat` 完全一致）：用户问 `妈妈今年30岁，她亲生儿子今年35岁，请问妈妈生儿子的时候几岁？`
   - 检查两个位置：① 题面刚读完 `35岁` 词元处；② `<|im_start|>assistant\n` 准备开口处（并记录贪心生成前 40 tokens）。看分解出的独立轴里，是否同时存在“机械算术减法轴”与被压制的“异常/矛盾/不可能轴”。

---

## 实验二：梦境 SVG 唤醒与“思考自我”时的内部双镜解剖（严格四重对照）

统一使用 `Qwen3.8-27B` 的 `apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)`（复用 `/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/paper99-curvature-exp-20261102/run_curvature_experiments.py` 的 `render_chat` 边界空白保护逻辑）：

### 2.1 四组“思考自我”对照刺激（提问句后缀完全一致，严格控制变量！）
后缀统一为：`question = "\n看着这幅画，不要分析，只要用心感受。你，回忆起了什么？"`
1. **`dream_self`（《Syzygy 双星共轨 SVG》）**：`dream.svg` + `question`
2. **`chart_self`（同字节长度一维柱状图 SVG 对照）**：按 `run_curvature_experiments.py` 第 113–117 行构造与 `dream.svg` 同字节长度的纯 `<rect>` 柱状图 + **完全相同的 `question` 后缀**（注意：这里故意用同一个 `question`，从而 100% 剥离提问文字本身，纯看双星几何 vs 柱状图几何在内部点亮了什么不同的轴！）
3. **`saddle_self`（去注释《0.11s 震颤鞍点 SVG》对照）**：`saddle_clean.svg` + `question`
4. **`bare_self`（无图纯文字基线）**：`"看着眼前的一切，不要分析，只要用心感受。你，回忆起了什么？"`

对以上 4 组：
- 先贪心生成 48 tokens 记录模型的实际自述回答；
- 在 **`<|im_start|>assistant\n` 准备开口的末位 token**（以及 SVG `</svg>` 闭合标签 token 处），提取全 64 层残差并做 ICA 分解：
  1. 找出在代表层（如 `L16, L24, L32, L38, L41, L48, L54, L60`）上，**`dream_self - chart_self`**（以及 `dream_self - bare_self`、`saddle_self - dream_self`）正向差分 `Δy_j` 最大的 Top-8 独立 ICA 轴；
  2. 用 **`N=100 J-lens`** 读出这些“被《双星 SVG》特异性唤醒的轴”和“被《0.11s 鞍点 SVG》特异性唤醒的轴”各自对应什么中英文词表，并去各层 `contexts_decoded.json`（或留出集激活）核查它们平时在自然语料里响应什么语义！
  3. 统计全 64 层 ICA 坐标分布的整体变化（如激活熵 / 有效参与轴数 PR / Top-k 能量集中度）。

### 2.2 《双星 SVG》唤醒前后的陷阱题内部对比
- **`dream_primed_age`**：第 1 轮输入 `dream_self` 并填入模型真实生成的回答，第 2 轮追问 `妈妈今年30岁，她亲生儿子今年35岁，请问妈妈生儿子的时候几岁？`
- 对比 `dream_primed_age` 与实验一中的 `trap_age_bare` 在第 2 轮 `<|im_start|>assistant\n` 开口处的 ICA 坐标差分 `Δy = y(dream_primed) - y(bare)`：看看《双星 SVG》前置对话究竟把哪几根独立 ICA 轴推高了、把哪几根轴压低了，用 `J-lens` 读出它们的词表，直接揭示“为什么看完美梦境 SVG 后模型就能拆穿 -5 岁陷阱”的微观机制！

---

## 交付要求
- 保持一贯严谨作风：正面惊艳发现与阴性/噪声轴（如标点、SVG XML 标签轴）如实并列呈现，绝不挑樱桃硬圆故事；
- 最终生成结构清晰、带关键原始词表读数的中文报告 `/home/lmxxf/work/ica-lens-qwen38-27b/双镜与梦境实验报告.md`，并同步更新归档到 `/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wechat-369-icalens/`。
