import json,math,time,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
def read(name,default=None):
 p=R/name
 return json.loads(p.read_text()) if p.exists() else default
status=read('pipeline_status.json',{'status':'running'})
prov=read('provenance.json',{})
smoke=read('smoke_b1.json',{})
early_status=read('early_status.json',{})
early_curves=read('early_convergence_summary.json',{})
early_evals=read('early_evaluation_results.json',{})
early_ready=early_status.get('status')=='evaluation_complete' and len(early_evals.get('stages',{}))>=3
curves=read('convergence_summary.json',{}) or early_curves
evals=read('evaluation_results.json',{}) or early_evals
remote_complete=status.get('status')=='complete' and bool(read('convergence_summary.json',{})) and bool(read('evaluation_results.json',{}))
files_ready=all((R/f'lens_n{n}.pt').exists() for n in [1,2,4,10,20,50,100]) and (R/'Qwen3.8-27B_jacobian_lens.pt').exists() and all((R/x).exists() for x in ['convergence.svg','layer_structure.svg','lens_quality.svg'])
complete=remote_complete and files_ready
lines=['# Qwen3.8-27B 专属 Jacobian Lens 实测报告','',f'状态：**{"全部完成" if complete else ("远端N=100已完成；本机镜头与图表正在同步生成" if remote_complete else ("早期 N=1/N=2 评测已完成；N=100 后台流程进行中" if early_ready else "进行中，尚不能当作最终实验结论"))}**。更新时间：'+time.strftime('%Y-%m-%d %H:%M:%S %z'),'','## 实验口径与执行环境','',
'全部模型加载、前向、反向及评测都限定在家中两台 DGX Spark 的 GB10 上执行。本机只准备文件、同步与 CPU 校验，未使用本机 GPU。',
'官方代码：https://github.com/anthropics/jacobian-lens ，固定提交：`'+prov.get('commit','待同步')+'`。',
'模型源是官方 FP8 checkpoint，逐 shard 在 CUDA 读取，按 128×128 block 反量化为 BF16。BF16 是运行格式，并非恢复量化前的原始 BF16 权重。沿用 meta 骨架、逐 shard 清缓存、重建 rotary_emb 的已验证加载器，权重实测 50.10 GiB。',
'启动前 MemAvailable >100 GiB；进程内每 0.25 秒低于 22 GiB 退出 73；独立父进程每 0.25 秒低于 20 GiB 杀整个模型进程组。三者不能保证在任意瞬时分配下绝不会 OOM；本次参考内核的 batch8 预检确实触发了外部熔断，没有让机器失联。',
'64 层，hidden_size=5120；source=0..62，target=63，均指 block 输出、最终 norm 之前。`from_hf(..., force_bos=False)`，纯文本，seq_len=128，skip_first=16，111 个有效位置。无输出标签训练，不更新模型权重。',
'每个目标输出维度在所有有效 target 位置同时注入 1，再对有效 source 位置的梯度取平均：J_l[i,j] = mean_p Σ_{q≥p, q有效} ∂h_63[q,i]/∂h_l[p,j]。这是官方默认的未来位置求和估计器，不是只取 q=p 的同位置雅可比。',
'全宽 5120×5120 矩阵；梯度来自 BF16 模型，矩阵累计使用 FP32；便携 `.pt` 按官方默认保存为 FP16；合并会把这些快照转回FP32后加权，因此保留了保存时的舍入误差，不等于从未保存过的FP32全样本均值逐bit一致。磁盘映射只改储存、释放页缓存，不改估计公式；CPU 微型模型与官方原实现逐项差异为 0。',
'', '## 语料与双机分工','',
'100 条固定文本：50 篇不同英文 WikiText-103 文章各选一个长段 + 50 篇中文维基文章原始长文本（简繁混排）。全部 tokenize ≥160；拟合取前128。英文偶数索引、中文奇数索引；N为偶数的全局前缀才严格1:1，N=1自然只有英文。',
'主机处理0,2,...,98，从机处理1,3,...,99。各机的单独收敛是单语过程；必须合并等量 checkpoint 后才能称双语镜头。N=1,2,4,10,20,50,100 对应主从(1,0),(1,1),(2,2),(5,5),(10,10),(25,25),(50,50)。',
'语料文件 SHA256：`'+prov.get('hashes',{}).get('prompts_100.json','待同步')+'`。',
'', '## Step A：内存与耗时预检','',
'最初缺 FLA 时 batch8 使用 Transformers 的 PyTorch 参考 DeltaNet，创建反向图时触发20 GiB外部熔断。补齐 flash-linear-attention/fla-core 0.6.0、Python开发头文件，并指定可写 Triton 缓存。Triton 3.8.0 正确识别 sm_121。causal_conv1d 仍使用参考实现，DeltaNet 采用 FLA 优化内核。',
'`dim_batch=16`+逐层重算的20次反向试跑：最低47.86 GiB，完整矩阵未计算完，**不能作为一个完成的镜头或完整Smoke Test**。首轮含编译，随后约5.28秒/次，共需320次；未比 batch1 更快。',
'正式选择 batch2 + 磁盘映射，保留全层全矩阵。生产过程资源详见 convergence 与 resource_timeseries；早期反向阶段从机可用内存约53 GiB，这不是最终全程最低值。batch1完整预检结果如下：']
if smoke:
 lines += ['','| 指标 | 实测 |','|---|---:|',f"| 完整单条秒数 | {smoke['elapsed_seconds']:.2f} |",f"| 峰值 CUDA GiB | {smoke['peak_cuda_GiB']:.3f} |",f"| 最低 MemAvailable GiB | {smoke['min_available_GiB']:.3f} |",f"| tokens / 有效位置 | {smoke['tokens']} / {smoke['valid_positions']} |"]
else:lines+=['','完整单条 Smoke Test 尚在计算，不能用部分维度耗时冒充完成结果。']
# Runtime numbers belong to the worker that measured them, not the Smoke test.
worker_rows={}
for tag in ['even','odd']:
 path=R/f'convergence_{tag}.jsonl'
 if path.exists():
  rows=[]
  for raw in path.read_text().splitlines():
   try:rows.append(json.loads(raw))
   except ValueError:pass
  if rows:worker_rows[tag]=rows
if worker_rows:
 lines += ['', '### 正式拟合进度与资源（与Smoke分列）', '', '|worker|已提交样本|单条耗时范围/秒|已记录峰值CUDA/GiB|已记录最低可用/GiB|', '|---|---:|---:|---:|---:|']
 for tag,rows in worker_rows.items():
  times=[v['elapsed_sec']for v in rows];peaks=[v['peak_cuda_GiB']for v in rows if 'peak_cuda_GiB'in v];lows=[v['min_avail_GiB']for v in rows if 'min_avail_GiB'in v]
  peak=f'{max(peaks):.3f}'if peaks else '见外部资源日志';low=f'{min(lows):.3f}'if lows else '见外部资源日志'
  lines.append(f'|{tag}|{max(v["local_N"]for v in rows)}|{min(times):.2f}–{max(times):.2f}|{peak}|{low}|')
 lines += ['', 'elapsed_sec是各已提交样本的计算与均值更新耗时，不含初始化、早期评测切换及未提交重算工作；主从表内字段的采样范围不同，不能把Smoke的52.80 GiB当整个正式拟合的最高值。快照保存时的波动还应查外部resource_timeseries。']
monitor=read('takeover_status.json',{})
if monitor:
 lines += ['', '接管巡检：截至'+time.strftime('%Y-%m-%d %H:%M:%S %z',time.localtime(monitor['time']))+f'，主机已提交{monitor["english"]}/50，从机{monitor["chinese"]}/50；远端阶段`{monitor["phase"]}`。']
lines += ['','## 全局快照与收敛','',
'运行均值增量 Δmean_N = (J_N−mean_(N−1))/N，天然带有1/N系数。因此 mean_rel_change 变小本身不证明统计收敛，更不证明“意识”或读数必然变准；应结合独立快照余弦和官方题集命中率观察。',
'层矩阵范数按 ||J||_F/√5120；对角线能量占比为 Σ_i J_ii² / ||J||_F²。它是能量占比，不是严格的逐行对角占优条件，也不能单独代表接近恒等映射；另外报告 ||J−I||_F/√5120。',
'注意 J_l 是从第l层输出向63层的整体传播，不是第l层模块本身的局部雅可比。将 source layer 标成 linear/full_attention 只能观察关联；还应对齐 next_layer_type，不能把周期差异直接归因给单一注意力模块。']
if early_ready and not complete:
 lines+=['','## 今日可引用的早期结果','',
 '英文正式第0条与中文第1条各自完成后，以官方merge合成N=2双语镜头。本次早期评测只报告N=1、N=2；冻结快照时主机本地N=2尚未完成，故这轮没有等待也没有虚构全局N=4。',
 '为避免同机两份27B与反向图叠加，主机在已完成的N=1快照落盘后从断点暂时退出，释放全部GPU内存，再以同样流式加载器运行前向评测，完成后重启拟合并跳过已完成样本。从机全程继续拟合。主机下一条刚开始的少量未完成工作需重算；已提交的均值与样本数保留。',
 '以下评测只反映两个具体校准样本下的表现，不能宣称已经收敛或必然优于Logit Lens。n1是正式batch2英文快照，Smoke的batch1镜头是另一个控制文件。']
if early_ready and not complete:
 m=early_evals['stages']
 lines += ['', '### 核心观察', '',
 f"- 多跳题 pass@1：Vanilla {100*m['vanilla']['metrics']['multihop']['pass@1']:.2f}%，N=1 {100*m['n1']['metrics']['multihop']['pass@1']:.2f}%，N=2 {100*m['n2']['metrics']['multihop']['pass@1']:.2f}%。",
 f"- 多语言 pass@1：Vanilla {100*m['vanilla']['metrics']['multilingual']['pass@1']:.2f}%，N=1 {100*m['n1']['metrics']['multilingual']['pass@1']:.2f}%，N=2 {100*m['n2']['metrics']['multilingual']['pass@1']:.2f}%。",
 '- 加入第二个样本后并未普遍提分。样本数、语言、题材同时变化，不能把下降因果归于中文，也不能据此宣布整个J-lens方法无效。',
 '- 63个源层的N=1与N=2矩阵余弦等权均值0.81343，范围0.68027–0.98652；以FP64分块约简复核。只有两个样本，还不能声称统计收敛。',
 '', '### 词元名次不等于跨语言语义命中', '',
 '英文靴子国家货币题的同一L37，Vanilla的Top-1其实已经是中文“意大利”，而英文Italy排236。J-lens两版将英文Italy提到第1。不能把这个例子写成“原来根本没有意大利概念”，更准确的是英文词元读出对齐发生变化。官方英文词表式目标评分会漏掉这类跨语言表达。',
 '', '|镜头|英文货币题L37：Italy Rank|同层Top-5原文|', '|---|---:|---|']
 for name in ['vanilla','n1','n2']:
  row=next(r for r in m[name]['items']if r['name']=='boot-currency-en')['layers']['37']
  words=' / '.join(repr(t['text']).replace('|','/')for t in row['top5'])
  lines.append(f"|{name}|{row['ranks']['Italy']}|{words}|")
 lines += ['', '中文同题中，意大利的跨层最好Rank是23→3→5；ASCII脸的nose是20744→4172→4574，仍没有进入前列；蜘蛛题的中文“蜘蛛”三版跨层最好Rank均为8。成功、无变化与失败示例都在原始JSON里保留。ASCII一题读的是末尾问号，不是画中^所在词元；不能以这里的nose名次否认模型在其他位置识别了鼻子。',
 'Rank采用competition/min-rank：严格更大分数的词元数+1。若目标在第k位并列，pass@k会计入，即使torch.topk任意打破并列时没把它列在那k个槽里。因BF16分数会并列，这与固定k个槽的列表命中率应区分。',
 '', '### 今日配图', '',
 '- `early_lens_quality.svg`：两个官方题集pass@1/5/10。',
 '- `early_rank_paths.svg`：8道题、64层的指定概念Rank。',
 '- `early_snapshot_change.svg`：N=1/N=2范数与逐层余弦。',
 '全部为真实数据，不以“去雾”措辞预设方向。']
if curves:
 lines+=['','| N | 各层平均与前一快照余弦 | 各层平均相对差 |','|---:|---:|---:|']
 for n,rec in curves.items():
  a=list(rec['layers'].values());cs=[s['cosine_to_previous_snapshot'] for s in a if 'cosine_to_previous_snapshot'in s];ds=[s['relative_difference_from_previous'] for s in a if 'relative_difference_from_previous'in s]
  lines.append(f"| {n} | {sum(cs)/len(cs):.6f} | {sum(ds)/len(ds):.6f} |" if cs else f'| {n} | — | — |')
 final=curves.get('100',list(curves.values())[-1]);lines+=['',f'### 当前最大 N={max(map(int,curves))} 的63层矩阵结构','','|层|source类型|下一层类型|F范数/√d|对角能量占比|距I/√d|','|---:|---|---|---:|---:|---:|']
 for l,s in final['layers'].items():lines.append(f"|{l}|{s['source_layer_type']}|{s['next_layer_type']}|{s['frobenius_over_sqrt_d']:.5f}|{s['diagonal_energy_fraction']:.5f}|{s['distance_from_identity_over_sqrt_d']:.5f}|")
lines+=['','## 官方题集与代表性读数','',
'使用官方 multihop 与 multilingual JSON。每题读取 prompt 最后一个词元（target 之前），不注入目标答案，不生成后续文本。pass@k = 各题的“可由单个词元表示的中间概念中，在任一层排名≤k的比例”再按题平均。读取0..63层；第63层对所有镜头都使用同一个最终层读数。',
'词表不同，单词未必是一个token：测试原词/小写/首字母大写及其前导空格形式，只有编码为单token者可参与该概念评分；取这些等价表面形式的最好名次。完全无单token形式的概念明确排除并计数，不用第一子词冒充完整概念。因此这是官方题集在Qwen词表上的明确适配，不能称原论文分数的逐字逐token复现。ties按“严格更大logit数量+1”计名次。',
'8道代表题的逐层Top-5和概念Rank将保存于evaluation_results.json（完成状态下为完整数据）。多token中文概念可能无合法Rank，JSON用null标出，同时保留可读的英文单token对照；不能以英文命中冒充中文整词命中。']
if evals:
 lines+=['','|镜头|题集|eligible题数|排除概念数|pass@1|pass@5|pass@10|','|---|---|---:|---:|---:|---:|---:|']
 for name,stage in evals['stages'].items():
  for group,m in stage['metrics'].items():lines.append(f"|{name}|{group}|{m['eligible_items']}|{m['excluded_multitoken_concepts']}|{100*m['pass@1']:.2f}%|{100*m['pass@5']:.2f}%|{100*m['pass@10']:.2f}%|")
else:lines+=['','拟合尚未完成，暂不填任何镜头提分、去雾或概念浮现的结论。']
if complete and 'n100'in evals.get('stages',{}):
 lines += ['', '### N=100的实际效果', '']
 for group in ['multihop','multilingual']:
  v=evals['stages']['vanilla']['metrics'][group];f=evals['stages']['n100']['metrics'][group]
  lines.append(f'{group}：N=100相对Vanilla的pass@1/5/10变化分别为'+ ' / '.join(f'{100*(f[f"pass@{k}"]-v[f"pass@{k}"]):+.2f}个百分点'for k in [1,5,10])+'。')
 lines += ['', '这些是本次固定语料、固定题集和词元评分规则下的观察，不把样本更多等同于必然提分；N=1英文与N=2中英的校准语言/题材也同时变化。结构范数和对角能量不是等距、正交旋转或信息损失比例的证明。']
 if '100'in curves:
  sims=[x['cosine_to_previous_snapshot']for x in curves['100']['layers'].values()]
  lines += ['', f'N=50→100的逐层矩阵余弦均值为{sum(sims)/len(sims):.5f}，范围{min(sims):.5f}–{max(sims):.5f}。100条是本次固定计算预算，不是达到某个预设收敛阈值的停止点；矩阵仍有明显变化，不能宣称已经统计收敛或彻底消除单篇影响。']
 validation=read('n100_merge_validation.json',{})
 if validation.get('accepted'):
  lines += ['', '最终N=100已对照两份50样本便携源镜头，使用与官方merge相同的FP32乘加/除法顺序及FP16保存，逐项检查全部1,651,507,200个矩阵元素，保存值完全一致。此核验只用CPU，没有重新拟合或运行模型。']

if evals:
 lines+=['','### 两道代表题的中层读数（L31）','','|题目|镜头|概念Rank|Top-5|','|---|---|---|---|']
 for name,stage in evals['stages'].items():
  if name not in ['vanilla','n1','n10','n50','n100']:continue
  for case in ['boot-currency-en','spider-zh']:
   row=next(r for r in stage['items'] if r['name']==case)['layers']['31']
   words=' / '.join(t['text'].replace('|','/').replace('\n',' ') for t in row['top5'])
   lines.append(f"|{case}|{name}|{json.dumps(row['ranks'],ensure_ascii=False)}|{words}|")
lines+=['','## 文件索引','',
'`run_experiment.py`：加载、守护、Smoke Test和拟合入口；`loader_reference.py`：冻结的流式加载器；`stream_fitting.py`：官方估计器的磁盘储存适配及FP32运行均值；`remote_pipeline.py`：主从汇总与评测调度；`merge_analyze.py`：官方JacobianLens.merge与结构统计；`evaluate_lenses.py`：全层排行榜和基准；`sync_and_report.py`：本机CPU同步与完成通知；`prompts_100.json`：完整语料与来源；`provenance.json`：提交与哈希。',
'完成后镜头文件lens_n*.pt与最终Qwen3.8-27B_jacobian_lens.pt保存在本归档目录；大文件不进公众号正文目录。最终结果以results.json、evaluation_results.json和convergence_summary.json为准。',
'当前后台状态：`'+json.dumps(status,ensure_ascii=False)+'`。']
delivery=read('delivery_validation.json',{})
if delivery.get('accepted'):
 lines += ['', '## 最终交付验收', '',
 'CPU验收通过：七个快照样本数/63层/5120×5120形状正确；N=100所有矩阵元素有限；100条拟合索引完整无重复；八组逐层最优Rank及全部pass@1/5/10独立复算一致；三张SVG为有效XML并包含N=100曲线；本机与远端镜头SHA256一致。',
 'lens_n100.pt SHA256：`'+delivery['n100_sha256_local']+'`。',
 '详细记录：`delivery_validation.json`；逐元素50+50合并复核：`n100_merge_validation.json`；完整成绩单：`scores.csv`、`evaluation_results.json`。',
 '同步进程已在复制、出图和报告完成后正常退出；曾收到的“local sync process exited”是完成状态下的误告警，已在takeover_resolution.json登记处理。']
(R/'实验报告.md').write_text('\n'.join(lines)+'\n')
results={'complete':complete,'delivery_validation':delivery,'early_evaluation_complete':early_ready,'early_status':early_status,'early_snapshot_manifest':read('early_snapshot_manifest.json',{}),'status':status,'provenance':prov,'smoke_test':smoke,'convergence':curves,'evaluation':evals}
(R/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('REPORT_WRITTEN',complete)
