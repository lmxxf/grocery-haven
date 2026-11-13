# eGPU-DX12-Booster · Phase 3 任务书（给闇 `wC:p1`：真机 3A 游戏病因定性与 A/B 帧率实测）

Zero 已授权今晚在客厅 `rtx5090` 上放开手脚实测真实游戏（家里没人，不用顾虑声音或桌面占用，但务必做好原始文件完整备份，测完恢复干净状态）。

## 赛前极其关键的硬件发现（必读！）
刚刚停掉闲置的后台 ComfyUI 后，`rtx5090` 的 `nvidia-smi -q` 依然显示：
`BAR1 Memory Usage: Total 32768 MiB, Used 32740 MiB, Free 28 MiB`！
结合你在 Phase 1/2 探针里测到的 `allocation type=5` 首次全量写入耗时：
- `4 MB`: `0.74 ms`, `16 MB`: `2.98 ms`（在 `28 MiB` 物理 BAR1 窗口内，满速 `5.4 GB/s`）；
- `24 MB`: `19.19 ms`, `32 MB`: `24.95 ms`, `64 MB`: `59.57 ms`, `256 MB`: `207.92 ms`（超过 `~20–28 MiB` 物理 BAR1 窗口后，WDDM/驱动靠滑动重映射 Aperture 分页，CPU 写入延迟暴增）！

这意味着在真实 3A 大作里有**三条必须分清的物理线索**：
1. 游戏原生到底创建了多少 MB 的 `DEFAULT(1)` / `UPLOAD(2)` / `READBACK(3)` / `CUSTOM(4)` / `GPU_UPLOAD(5)`？有没有游戏/插件自己申请了 `CUSTOM L1` 把 28MB BAR1 挤爆？
2. 游戏每帧的 `rxpci` / `txpci`（`nvidia-smi dmon -s uct -d 1`）到底是多少 MB/s？`Present` 真实 FPS 是不是 30–40 FPS？
3. 在 `mode=1` 下，**严守物理 BAR1 窗口的甜点配额（如 `max_total_mb=20`）** vs **大配额（如 `max_total_mb=256`）** 分别对真实游戏 FPS 产生什么变化？

---

## 执行步骤

### Step 1：给 `telemetry.cpp` 补一行全堆类型驻留账本（v0.2.1 小增强）
在 `dxgi.dll` 日志里增加对游戏创建的所有 Heap / CommittedResource 按 `Type=1..5`（以及 `CUSTOM` 中 `MemoryPoolPreference == L1`）的累计创建数与当前存活字节数 `live_bytes_by_type[1..5]` 统计，编译更新 `build/dxgi.dll`。

### Step 2：备份 `rtx5090` 游戏目录并查清 Steam AppID
1. 查看 `D:\SteamLibrary\steamapps\appmanifest_*.acf`，确认 **《影之刃零》（`PBZ`）** 与 **《黑神话：悟空》（`BlackMythWukong`）** 的准确 AppID 与启动路径；
2. 将 `D:\SteamLibrary\steamapps\common\PBZ\platform\steam\` 下原有的第三方注入文件（`dxgi.dll`, `fakenvapi*`, `OptiScaler*`, `amd_fidelityfx*`, `dlssg*`, `libxe*`, `nvngx*` 等非原版文件——注意核对时间戳，原版文件与 `PBZ.exe` / `steam_api64.dll` 同批，第三方文件是 11月4日放进去的 DLSS5 移植包）完整备份移入 `C:\Temp\egpu_backup\PBZ_thirdparty\`，先拿到 **100% 纯净原版 `PBZ`**！
3. 备份 `C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows\GameUserSettings.ini` 到 `C:\Temp\egpu_backup\`，并在测试配置中将：
   - `FrameRateLimit_WhenBackgrounded=0.000000`（防止窗口未获焦点时被假性锁 30 帧！）
   - `bUseVSync=False`（排除电视 30Hz/60Hz 垂直同步锁帧干扰，同时顺手查一下桌面当前真实分辨率和刷新率！）

### Step 3：在 `rtx5090` 交互会话（Session 2）拉起游戏采集 `mode=0` 真机 X 光
在 `seth` 所在的桌面会话运行游戏（《影之刃零》优先，若主菜单需要按键进入游戏/继续存档，可在启动稳定后观察标题 3D 场景 FPS，或进入存档关卡测试；《黑神话：悟空》亦可对照测试）：
1. 同步在后台采集 `nvidia-smi dmon -s uct -d 1` 连续 45–60 秒日志（记录 `sm`, `mem`, `rxpci`, `txpci`）以及 `nvidia-smi --query-gpu=pcie.link.gen.current,pcie.link.width.current,memory.used,utilization.gpu --format=csv -l 1`；
2. 收集 `mode=0` 下的 `egpu_booster.log`（确认 `presents`、`fps`、`frame_median_ms`、`upload_bindings`、`cbv/srv_upload_creates`、`upload_default_bytes`、`default_readback_bytes`、`live_bytes_by_type`）；
3. 优雅关闭游戏进程，保存完整日志到本地 `/home/lmxxf/work/egpu-dx12-booster/build/phase3/`。

### Step 4：基于 Step 3 实测病因跑 `mode=1` 分档对照（及必要时的针对性策略）
- 在完全相同的场景/流程下，对比：
  1. `mode=0`（纯净基线）；
  2. `mode=1` 窄窗口甜点档（`max_total_mb=20`, `max_buffer_mb=8`, `max_heap_mb=16` —— 贴合 28MB Free BAR1）；
  3. `mode=1` 宽窗口档（`max_total_mb=256`, `max_buffer_mb=64`, `max_heap_mb=128`）；
- 记录每组的真实 **FPS、FrameTime 中位数/P99、`rxpci / txpci` MB/s 变化**！
- 测试全部完成后，先将游戏目录恢复干净（或保留你验证最优的配置并在报告中写明备份还原方式），把全部真实数据与结论写入 `/home/lmxxf/work/egpu-dx12-booster/docs/phase3_game_results.md` 汇报！
