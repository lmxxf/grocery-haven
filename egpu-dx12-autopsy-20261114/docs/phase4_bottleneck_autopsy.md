# Phase 4 · 4K DLSS 性能档瓶颈解剖

测试日期：2026-11-14。主机 `rtx5090` / `NucBox_EVO-T1`，Core Ultra 9 285H、RTX 5090 32GB、驱动 621.14。诊断代理 v0.3/v0.3.1。

## 结论与收尾

**本轮没有稳定复现“30–50FPS 且 GPU≤60%”的原现场，因此不能声称已经找到了单一真凶。** 但阻塞探针已跑通，且抓到了一个重要的归因陷阱：约 12–14ms/帧的已识别 Fence 等待集中在 `RHIInterruptThread`，不能直接写成 Game/Render/RHI 线程被读回堵住了这么久。

悟空完整 Benchmark 官方结果为平均 **74FPS**、最高85、最低27，95%帧高于64；主体采样 GPU 中位约91%。PBZ 性能档静态约69.04FPS，山谷开阔视角持续转镜约65.93FPS，GPU平均均约74%，未形成目标稳态。

**收到收尾指令后没有再换存档、没有增加实验。** 当前组采完后停止了输入，两款游戏均关闭，测试代理/INI/log 已从游戏目录移除；PBZ配置、独立设置SAV、SaveGames、ProfileNLP及悟空配置均按备份还原并逐文件核验。

## 参数校正：4K 输出不等于原生 4K

PBZ 本轮进入画质页时，UI 明确显示原设置为 **DLSS“质量”**，随后才选择并应用 **“性能”**；FG关闭，Reflex关闭，动态分辨率关闭。输出为3840×2160。参数证据为 `pbz_graphics.png` 和 `pbz_performance_verified.png`。

因此，不应把此前仅核实输出分辨率的 Phase 3 记录补记成“纯原生4K”。本轮也没有独立采集 DLAA/禁超采样的纯原生对照；文件名 `pbz_loaded_native.png` 是早期命名，不构成原生采样证据。此前数据应称“4K输出、原设置”，不能据此计算“原生→DLSS性能”的精确加速比。收到停止指令后没有为补齐这个标签追加采样。

悟空已在 UI 与结果页核实：3840×2160、DLSS清晰度50、帧生成关闭、VSync关闭。改4K后曾自动落到33%，已明确调回50并应用。光追沿用原开启状态，结果页标“高”；没有为了制造低占用而人为限帧。

## 实验范围与原始数据

| 数据集 | 场景/口径 | dmon样本 | 有效代理窗口秒数 | Present/帧时样本 |
|---|---|---:|---:|---:|
| `wukong_dlss_perf_base` | 自动Benchmark；脚本剔除明确菜单/加载窗口后 | 150 | 132.594 | 8936 |
| `pbz_dlss_perf_static` | 木屋存档点，性能档静态 | 45 | 48.235 | 3330 |
| `pbz_dlss_perf_orbit` | 先移动/转向到山谷开阔视角，再持续环视 | 60 | 64.297 | 4239 |

PBZ 先执行约3秒前进、2秒后退并调整视角；正式动态采样主体是70秒持续环视，dmon采60个一秒样本。它不是另一个存档，也不是长距离战斗跑图。截图 `pbz_open_view.png`、`pbz_large_area.png`、`pbz_broad_view.png` 与 `motion_status.txt` 记录路径和输入结果。

窗口秒数含采集启动/边界开销，FPS由真实 `dt_s` 和Present数量计算，不是帧数硬除以45/60。帧时按每快照批量保存的单帧间隔合并计算，中位数与上侧经验P99。

PBZ全采样均Gen4×4。悟空包含加载/闲置阶段的Gen1/2/4记录；GPU利用率≥60%的query记录均为Gen4×4，不能把空闲降代当成活动瓶颈。两款进程在交互Session 2运行；悟空核实为Normal优先级，未修改全局CPU亲和性或电源计划。

## 帧率、帧时与 PCIe 流量

| 记录 | FPS | 帧时中位 ms | P99 ms | GPU平均 / 中位 % | RX平均 MB/s | TX平均 MB/s |
|---|---:|---:|---:|---:|---:|---:|
| 悟空：脚本筛选窗口 | 67.39 | 13.829 | 21.487 | 80.2 / 91.0 | 907.7 | 384.7 |
| PBZ：性能档静态 | 69.04 | 14.399 | 16.742 | 74.6 / 75.0 | 1664.8 | 313.6 |
| PBZ：山谷转镜 | 65.93 | 15.039 | 18.371 | 73.7 / 74.0 | 1657.8 | 312.7 |

**悟空官方完整计分与脚本窗口不是同一统计口径。** 官方结果页74FPS覆盖游戏自己的完整计分段；脚本筛选窗口仍含首次入场尾部，且150条dmon包含菜单/加载。不能把脚本67.39FPS或整段GPU平均80.2%冒充官方完整运镜均值。完整结果截图 `wukong_benchmark_final.png` 保留全部参数和曲线。

悟空仅有两个约2秒窗口满足数值门槛：

| UTC结束时间 | FPS | query GPU平均 % | 已识别Fence等待 ms/Present |
|---|---:|---:|---:|
| 2026-11-13T17:32:15.955Z | 37.72 | 1.5 | 26.181 |
| 2026-11-13T17:32:23.998Z | 49.50 | 50.5 | 19.493 |

两段均在测试早期，彼此不连续；其中GPU1.5%的窗口尤其不能作为稳定大场景现场。PBZ两组没有满足门槛的窗口。不能把偶发的最低27FPS或单个两秒窗口替代用户描述的持续状态。

## CPU API 内部耗时

以下是完成调用的QPC墙钟耗时，按Present归一化，单位ms/Present；不是CPU指令活跃时间，也不是可以直接相加的一帧预算。

| 原始API类别 | 悟空筛选段 | PBZ静态 | PBZ山谷转镜 |
|---|---:|---:|---:|
| Present | 0.419959 | 0.418945 | 0.417499 |
| ExecuteCommandLists | 1.057433 | 2.160035 | 2.309067 |
| Map(UPLOAD/GPU_UPLOAD) | 0.035550 | 0.000008 | 0.000007 |
| Map(READBACK) | 0.001729 | 无调用 | 无调用 |
| 识别到的Fence事件等待 | 14.290025 | 12.624572 | 13.176932 |
| SetEventOnCompletion登记 | 0.101722 | 0.299296 | 0.332477 |
| GetCompletedValue轮询 | 0.012529 | 0.039712 | 0.043275 |

PBZ每帧Execute调用约 89.6 / 98.0 次；识别到的Fence等待调用约 71.7 / 79.5 次，包含短等待/轮询，不能每次都按独立跨桥往返估价。

- 三组识别到的Fence等待都集中在 `RHIInterruptThread`。PBZ关键Game/Render/RHI/Submission线程没有直接归入该HANDLE集合的Fence等待，另有大量普通任务等待；尚未建立它们与通知线程之间的依赖链，不能据此完全排除间接GPU依赖。
- PBZ的Map(READBACK)在采样窗口内没有调用，UPLOAD Map也仅有极少量。持久映射后的CPU读写、memcpy不在Map函数计时范围内；不能把“Map快/无调用”写成“没有读回成本”。
- 所有线程的其他Wait总数可达数百ms/Present：它是几十个后台线程并行等待的累加，并不代表一帧停了几百ms。不能与Present/Exec/Fence拼成耗时饼图。
- 本次这些场景里，Present约0.42ms、Exec约1.1–2.3ms，并没有测到它们本身持续吃掉10–20ms；对未复现的原场景不能外推。

### 外部线程 CPU 活跃时间

从Windows线程CPU累计值做差，避免把QPC等待当成忙碌。以下为单线程占一个核的比例，不是整机CPU占比。

| 线程 | PBZ静态 %单核 | PBZ转镜 %单核 |
|---|---:|---:|
| GameThread | 39.6 | 39.8 |
| RenderThread_0 | 41.6 | 40.8 |
| RHIThread | 57.1 | 57.9 |
| RHISubmissionThread | 32.6 | 32.3 |
| RHIInterruptThread | 12.0 | 13.3 |

RHIThread大约对应8–9ms/帧的活跃CPU工作；这提示API外的命令录制/驱动或场景工作值得区分，但这些数据并没有证明单核打满，更没有把该时间进一步分解到具体游戏/驱动函数。本轮未追加ETW或CVAR控制实验，不能把这点升级成已确认根因。

## Buffer / Texture 拷贝拆分

下表是已拦截拷贝的字节数/有效秒数，MB/s，不是硬件PCIe吞吐；重复记录的命令列表与未执行录制可能影响它与真实执行量的对应。

| 路径 | 悟空筛选段 | PBZ静态 | PBZ转镜 |
|---|---:|---:|---:|
| UPLOAD→DEFAULT Buffer | 266.190 | 433.577 | 446.692 |
| UPLOAD→DEFAULT Texture | 31.778 | 0.034 | 0.903 |
| DEFAULT→READBACK Buffer | 224.795 | 84.449 | 80.673 |
| DEFAULT→READBACK Texture | 未知（8572次未定体积） | 0.000 | 0.000 |

悟空使用v0.3：已知Texture字节为footprint估计，READBACK Texture仍有未定体积调用，绝不按0流量解释。PBZ使用v0.3.1：对非空SourceBox补入GetCopyableFootprints缓存，记录逻辑载荷，行padding不混入；两套Texture字节口径不用于跨游戏精确比较。

PBZ转镜Texture上传约0.90MB/s，Buffer上传约446.69MB/s，Buffer读回约80.67MB/s；这些当前数据没有显示持续4–6GB/s的硬件接收流量。硬件RX约1.66GB/s，仍不能由一秒平均值排除更短的突发或延迟限制。

### PBZ读回调用尺寸分布

| 尺寸 | 静态调用数 | 转镜调用数 |
|---|---:|---:|
| ≤4KiB | 3329 | 4278 |
| >4KiB且≤64KiB | 14428 | 18374 |
| >64KiB | 6659 | 8480 |
| 未知 | 0 | 0 |

这些是请求尺寸桶，不等于遮挡查询/流送/HZB的语义标签。不能只凭小拷贝数量就断言是哪一个UE子系统。

## 探针实现、验证与覆盖边界

- QPC计时放在原始API调用体两侧：Present/Present1、Execute、按堆类型分类的Map、Fence登记/轮询，以及四种Win32 Wait。空HANDLE的SetEventOnCompletion本身同步等待，单独归入Fence等待。
- 最近64个Fence事件句柄、成功登记后关联、CloseHandle时清除；混合多对象等待单独标记，保留返回值和LastError。长于500µs的次数、最长调用、线程名/ID和调用点RVA均落盘。
- 后台输出快照，避免批量日志写入阻塞Present；排除CEF的Present作为主画面帧源，日志保留swapchain窗口/尺寸证据。悟空补上从实际SwapChain Queue回溯设备的捕获及晚发现资源分类。
- PBZ显式使用 `track_bindings=0, track_descriptors=0` 精简模式，不在每次Root/Descriptor绑定上维护区间统计；否则可能干扰CPU受限场景。旧字段中的绑定0不能解释为游戏不使用UPLOAD。
- 受控自检覆盖Single/SingleEx/Multiple/MultipleEx等待与空事件同步等待；5组人为延迟均捕获，64KiB纹理上传/读回数据逐字节验证通过；v0.3.1还覆盖非空SourceBox路径。产物为x64，C++运行库静态链接，依赖仅系统DLL，20个DXGI导出与ordinal检查通过。
- 正式三组 `hook_failures=0`、事件环无驱逐。PBZ线程槽无溢出；悟空固定128线程槽出现60次溢出，全局计时仍累计，但不能声称逐线程覆盖所有线程。关键Game/Render/RHI/Submission/Interrupt线程已捕获。
- 只捕获应用模块IAT覆盖到的Wait；直接系统调用、未覆盖的动态解析入口、其他同步API、Sleep、驱动内等待、CPU memcpy及多数命令录制API并未被完整分解。QPC调用耗时还包含线程被调度走的时间。
- 完成调用的耗时在完成窗口累计，跨窗口长等待可能落到后一个窗口；多线程重叠、嵌套API与GPU执行使它不是加法式帧预算。
- 未做本轮无注入/关闭计时的帧率对照，因此不提供探针对FPS精确开销的保证；不能直接拿本轮精简模式与Phase3不同版本算优化收益。

## 恢复核验

备份：`C:\Temp\egpu_backup\phase4\`，包括悟空原Windows配置和PBZ原配置、安装目录SaveGames、三份独立设置SAV、ProfileNLP，PBZ有恢复前备份哈希清单。测试后状态另存归档，避免覆盖掉排查材料。

已停止输入并释放W/A/S/D与修饰键，随后关闭两款游戏。PBZ恢复38个文件、悟空恢复27个配置文件，全部哈希一致。测试DLL/INI/log已从游戏目录移除；旧诊断DLL若被系统暂时占用，移出游戏目录到 `D:\Temp\egpu_backup\phase4_used_proxy\`。没有把Phase3归档的旧OptiScaler包重新装回。原始游戏EXE及原生依赖未改，临时计划任务 `eGPU-Phase4-Desktop` 已删除。

核验结果：

```json
{
  "PBZProcesses": 0,
  "WukongProcesses": 0,
  "PBZProxyPresent": false,
  "WukongProxyPresent": false,
  "PBZRestoredFiles": 38,
  "WukongConfigRestoredFiles": 27,
  "AllRestoreHashesMatch": true
}
```

没有启动WPR录制，没有新增持久系统/驱动设置，也没有执行猜测性CVAR组合。正常游戏生成的缓存不作为注入文件清除。

## 文件索引

- `src/telemetry.cpp`、`src/profiler.h`：v0.3.1实现；`build/dxgi.dll`：最终交付。
- `src/profiler_smoke.cpp`、`build/phase4/profiler_smoke*.log/.txt`：计时/纹理自检。
- `build/phase4/wukong_dlss_perf_base/`：150条dmon、query、原始窗口/完整日志、参数、标记、分析JSON。
- `build/phase4/pbz_dlss_perf_static/`、`pbz_dlss_perf_orbit/`：45/60条dmon，时间戳、线程CPU起止值、完整/窗口日志、参数、分析JSON。
- `build/phase4/wukong_final/`、`cleanup/`：采集后完整日志、目录与恢复核验。
- `build/phase4/data_sha256.json`：主要数据文件SHA256清单。
- `scripts/phase4_analyze.py`：可重算摘要；Wukong窗口筛选为5<FPS<150且窗口中位帧时≥7ms，不能视为官方计分算法。扩展覆盖统计见各analysis.json。
- `scripts/phase4_collect.ps1`、`phase4_cleanup.ps1`：采集、停止及还原流程。

最终DLL SHA256：

```text
14abac0bebfde2a6184e8d16f2e883e42dd6384493f3c2eeffb61813f831664e
```

**本轮最终归因：尚未锁定原症状的单一根因。** 已有证据不支持把“全线程Fence等待总数”直接当作主线程PCIe阻塞，更不足以宣称UPLOAD提拔、关闭遮挡或增加缓冲已经解决问题。完整数据保留，按要求到此收尾。
