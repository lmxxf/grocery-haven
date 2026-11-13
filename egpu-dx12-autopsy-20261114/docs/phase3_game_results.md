# Phase 3 · PBZ 真机 A/B 与 PCIe 遥测报告

测试时间：2026-11-13 深夜至 11-14 凌晨（Asia/Taipei）。主机 `rtx5090` / `NucBox_EVO-T1`，RTX 5090，驱动 621.14。版本 **v0.2.1**。

## 结果先说

**真实游戏的提拔路径已跑通，但本场景没有得到合成微基准的巨大收益。** 三组同存档、同镜头、人物不动：基线 66.00FPS，20MiB 档 66.62FPS，256MiB 档 63.44FPS。窄档不到 1% 的差异不能称为稳定提速；宽档本轮约慢 3.9%。宽档降低了 PCIe 发送流量，却没有降低接收流量，也没有换来 FPS 收益。

已完成旧补丁/INI 备份、真实关卡三档测试、全类型分配账本、完整采样日志与清理。**游戏已关闭，测试 DLL/INI/log 已移除，原始 GameUserSettings.ini 已按 SHA256 验证恢复。旧 OptiScaler/DLSS5 文件留在备份，不重新塞回游戏。**

## 条件与场景

- Steam AppID：PBZ **4115450**；悟空 **2358720**（本轮无需启用，结果范围仅 PBZ）。PBZ buildid `26367565`。
- 渲染 EXE：`D:\SteamLibrary\steamapps\common\PBZ\platform\steam\PBZ.exe`；原生 Steam 启动器位于 `PBZ\steam\PBZ.exe`。
- 在用户 `seth` 的交互 **Session 2** 启动，沿用 Steam 正常渲染进程参数 `ProjectPBZ -basedir="...\ProjectPBZ\Binaries\Win64" -pc-platform=Steam`。Steam 首次启动曾等待 Shader Depot 检查；后续使用相同渲染 EXE/参数及 Steam AppID 环境，不修改 DRM/游戏二进制。
- 桌面及游戏 **3840×2160、60Hz**，全屏无边框，沿用原画质。进入“继续游戏”存档，站在木建筑前的香火/交互点，不移动、不战斗、不换装备；三组截图确认相同位置和视角。截图见 `after_vsync_off.png`、`narrow_level.png`、`wide_level.png`。
- `FrameRateLimit_WhenBackgrounded=0`；帧率限制关闭。初始 INI 编辑被游戏回写，曾出现约 60FPS 限制；随后在游戏显示设置中实际关闭 VSync，确认 UI 显示关闭、INI 为 `bUseVSync=False`、帧率超过 60，再做正式三组。受限窗口单独保留，不混入正式 A/B。
- 所有正式组使用同一 DLL；`spoof_heap_properties=0`，每档独立重启并加载相同存档，等待关卡稳定后采样。每组 **60 条 dmon 一秒样本**、63 条 GPU query；日志窗口含采样工具启动开销，统计采用实际 `dt_s`，没有硬拿帧数除以 60。

## FPS、帧时与总线流量

帧时为代理观察到的 Present 调用间隔，批量保存每帧样本后合并计算中位数/P99；不是显示器扫描计数，也不额外计算驱动生成帧。吞吐单位按 dmon 标注 MB/s。

| 配置 | FPS | 相对基线 | 帧时中位 ms | P99 ms | RX 平均 MB/s | TX 平均 MB/s | SM 平均 % |
|---|---:|---:|---:|---:|---:|---:|---:|
| mode=0，未限帧 | 66.00 | +0.00% | 15.072 | 17.711 | 1563.2 | 302.8 | 80.2 |
| mode=1，20MiB 窄档 | 66.62 | +0.95% | 14.943 | 17.471 | 1589.9 | 295.7 | 80.6 |
| mode=1，256MiB 宽档 | 63.44 | -3.87% | 15.718 | 18.035 | 1630.4 | 197.1 | 70.2 |

三组整个 query 窗口均为 **PCIe Gen4 ×4**。显存时钟中位均 14001MHz，核心时钟中位分别为 2827/2835/2835MHz；温度范围如下，不存在把空闲 Gen2 当作负载链路的误判。

| 配置 | 有效遥测秒数 | 帧时样本数 | GPU 温度 °C | dmon/query 行数 |
|---|---:|---:|---:|---:|
| mode=0，未限帧 | 63.641 | 4200 | 59.73–64.40 | 60/63 |
| mode=1，20MiB 窄档 | 64.844 | 4320 | 55.01–61.72 | 60/63 |
| mode=1，256MiB 宽档 | 64.313 | 4080 | 54.98–60.29 | 60/63 |

VSync 受限对照另存 `build/phase3/baseline/`：59.89FPS，中位 16.663ms，P99 18.492ms。它只能用于识别同步上限。

## 全堆类型账本与提拔确实生效

**这是仍存活的 owner 分配字节数，不是 WDDM 物理驻留/BAR 映射量。** Committed Buffer 按 Width，纹理按 GetResourceAllocationInfo 估算，显式 Heap 按 SizeInBytes；Placed 不重复计费。下表为采样窗口各快照中位数，单位 MiB。

| 配置 | DEFAULT(1) | UPLOAD(2) | READBACK(3) | CUSTOM(4) | GPU_UPLOAD(5) | CUSTOM L1 |
|---|---:|---:|---:|---:|---:|---:|
| mode=0，未限帧 | 5717.516 | 187.958 | 18.188 | 0.000 | 0.000 | 0.000 |
| mode=1，20MiB 窄档 | 5621.391 | 156.000 | 18.188 | 0.000 | 19.958 | 0.000 |
| mode=1，256MiB 宽档 | 5589.391 | 8.000 | 18.188 | 0.000 | 131.958 | 0.000 |

基线未观察到原生 CUSTOM L1 或 GPU_UPLOAD owner 分配；Type=5 出现在提拔组。

| 配置 | Committed 提拔累计数 | Heap 提拔累计数 | 提拔峰值 MiB | 末快照存活 MiB | fallback | 每帧普通 UPLOAD 根/VB/IB 绑定数 |
|---|---:|---:|---:|---:|---:|---:|
| mode=0，未限帧 | 0 | 0 | 0.000 | 0.000 | 0 | 4520.4 |
| mode=1，20MiB 窄档 | 42 | 0 | 20.000 | 19.958 | 0 | 1227.2 |
| mode=1，256MiB 宽档 | 169 | 2 | 255.958 | 163.958 | 0 | 0.0 |

- 窄档实际稳定存活约 19.96MiB，配额峰值不超过 20MiB；宽档有 **2 个显式 Heap** 提拔，覆盖游戏池化路径，且大量热绑定已转到 GPU_UPLOAD。所有正式快照 `hook_failures=0`，无创建 fallback，未观察到显式非空 Map 读取声明。
- 宽档的普通 UPLOAD 根/VB/IB 绑定计数降为零，promoted 根绑定持续增长，画面正常。因此不能把“没提速”解释为“DLL 没起作用”。
- 创建数是进程启动以来累计数，不能跨不同进程运行时长直接比较频率；Placed 不纳入 owner 提拔数量。存活量会随引擎池修剪波动，宽档 256MiB 是限额，不是全程占用。
- CBV 描述符创建计数为零并非错误：本场景大量使用 Root CBV，同时有大量 SRV 创建。完整创建/Map/Resolve/Fence 计数见日志。绑定池字节数不是 GPU 实际读取量，不能用“整池大小 × 绑定次数”冒充 PCIe 流量。

## 病因定性：能说到哪里

1. **存在真实 UPLOAD 绑定，但本场景的总体瓶颈没有被该提拔策略明显解除。** 32MiB × K 次完整重读的合成数据，不等于游戏每次绑定都会完整读取整块池；游戏实际读取范围、缓存、复制到 DEFAULT、队列同步等都不同。
2. 宽档把大量缓冲迁入 GPU_UPLOAD，TX 从约 303 降到 197MB/s，RX 却从约 1563 升到 1630MB/s，FPS 本轮反而下降。它改变了传输/访问路径，却没有消除主导帧时的成本；不能只展示 GPU 阶段微基准倍数。
3. 本次 20MiB 档与基线不足 1% 差异，不能据此宣布“物理 BAR 最优甜点”。宽档更慢也**不能直接证明**是 WDDM 滑窗分页：未采 page fault/Map 时间线或 CPU/GPU profiler。NVML BAR1 Free=28MiB 不能直接等同于本进程 GPU_UPLOAD 的容量硬限额。
4. 清理已识别旧注入后，此位置基线约 66FPS，**没有复现原来的 30–40FPS**；没有对原旧补丁堆栈做同位置 A/B，因此也不能认定旧补丁就是原问题根因。战斗、其他区域、低分辨率以及悟空均不在本轮结论范围。
5. 每档只有一轮、固定顺序，资源池/后台流送与温度并非逐字节相同。报告原样保留数值，不把小差异写成统计显著收益。一秒平均流量不能排除更短的 PCIe 突发或同步延迟问题。

## 为真实游戏补上的兼容性修复

- 初版启用遥测后启动失败；原版和 enabled=0 纯转发能进入标题。日志抓到 Factory 转发递归。修复组合：预先缓存系统入口、原始 GetProcAddress 使用原子指针、不再把显式系统-DXGI Factory 查询全局替换成自己的包装函数，并将后台工作延后到 Factory 创建后；D3D12CreateDevice 转发增加重入保护。
- PE 导入扫描增加 RVA/镜像边界检查，避免在早期解包/装载阶段盲读。
- 补齐受支持的 Device1–16 / GraphicsCommandList1–12 / CommandQueue1 继承 vtable，涵盖新版 TryCreate CBV/SRV、CommittedResource4/PlacedResource3；从 SwapChain 所持实际 Queue 补钩子，解决旧版漏记。
- 增加 owner 类型累计创建数、存活字节、CUSTOM L1，以及批量每帧时间样本。删除逐次释放写日志，避免真实游戏高频分配时产生不必要 I/O。
- 包含多次静态/动态 Factory 创建的补充 smoke 三档通过；最终三组真实关卡稳定运行，无 hook 失败。没有指令 detour 或修改游戏 EXE/DRM。

## 备份、清理与可复现入口

备份目录 `C:\Temp\egpu_backup\`：

- `PBZ_thirdparty\`：旧代理/DLSS5/OptiScaler 包共 **35 个文件**（含相关子目录），移动前记录 SHA256，移动后与收尾时两次核对。
- `PBZ_thirdparty_manifest.json`：原相对路径、长度、时间戳、哈希。
- `PBZ_GameUserSettings.original.ini`：原始 INI；`PBZ_Config_Windows\`：完整配置备份；另留测试 INI。

收尾已验证：PBZ 进程数 0，测试 dxgi.dll/egpu_booster.ini/log 均不存在，原 INI 哈希一致，桌面临时计划任务删除。游戏目录只剩原 `D3D12\`、`PBZ.exe`、`steam_api64.dll`、`tbbmalloc.dll`。这里只证明已识别注入已移除，没有运行 Steam 全库 Depot 校验。

若明确要恢复测试前的旧 OptiScaler/DLSS5 堆栈，已有 **未执行** 的 `scripts/phase3_restore_old_patches.ps1`，也放在远端 `C:\Temp\egpu_probe\`。它先校验备份与目标冲突，关闭游戏后可运行；保留备份。默认当前保持清洁原版目录，不保留任何“最优”测试注入。

复现工具：

- `phase3_prepare.ps1 -Case baseline/narrow/wide`：写三档配置。
- `desktop_agent.ps1` / `desktop_command.py`：交互 Session 2 启动、输入与截图；临时任务收尾已移除。
- `phase3_collect.ps1 -Label ... -Seconds 60`：dmon、GPU query、日志字节窗口、进程/时间元数据。
- `python3 scripts/phase3_summarize.py`：重算摘要，并核验三档参数、60 条 dmon、链路、帧样本和 quota。
- `phase3_cleanup.ps1` / `phase3_final_verify.ps1`：收尾与独立核对。

数据目录：`build/phase3/baseline_uncapped/`、`narrow20/`、`wide256/`；各含完整/窗口日志、dmon、query、INI、起止进程和时间元数据。`baseline/` 是额外 VSync 控制。`summary.json` 是机器可读摘要。部分长连接返回 SSH 255，但脚本的结束元数据、结束进程、全部 60 条 dmon 和 63 条 query 均已写完并验收；没有把连接退出码冒充游戏失败。

最终核对原文：

```json
{
    "PBZProcesses":  0,
    "ProxyPresent":  false,
    "TestIniPresent":  false,
    "TestLogPresent":  false,
    "OriginalIniRestored":  true,
    "TaskPresent":  false,
    "TemporaryProxySHA256":  "529B3B7E9C53959D0CCB283BEA713272F458AF0F5B85327665E570DACE9403BA"
}
```

DLL SHA256（本地与远端相同）：

```text
529b3b7e9c53959d0ccb283bea713272f458af0f5b85327665e570dace9403ba
```

源码、脚本、原始数据均保留在本项目；无对外发布。
