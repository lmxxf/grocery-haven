# eGPU-DX12-Booster · Phase 1 任务书（给闇 `wC:p1`）

## 背景与刚刚在 `rtx5090` 真机上抓到的重磅物理事实

1. 我们现在位于北京家中 `spark-3a10`，可通过 `ssh rtx5090` 免密直连客厅 Windows 11 主机（`Intel Core Ultra 9 285H` + OCuLink 外接 `NVIDIA GeForce RTX 5090 32GB`，驱动 `621.14`）。
2. `rtx5090` 的 `D:\SteamLibrary\steamapps\common\` 下三大靶标游戏全齐：
   - `PBZ`（《影之刃零》，注意其 `platform\steam\` 下目前有 11 月初测 DLSS5 留下的 OptiScaler `dxgi.dll`，后续游戏实测前需先移入备份目录测纯净基线）
   - `BlackMythWukong`（《黑神话：悟空》，100% 纯净原版）
   - `RESIDENT EVIL requiem BIOHAZARD requiem`（《生化危机 9》）
3. **刚刚在 `rtx5090` 上拍出的关键硬件 X 光（粉碎了盲目依赖 ReBAR 的幻想！）**：
   - `nvidia-smi` 显示链路上限为 **PCIe Gen4 x4**（空闲降频 Gen2 x4，负载升 Gen4 x4）；
   - **`nvidia-smi -q` 报 `BAR1 Memory Usage: Total 32768 MiB, Used 32740 MiB, Free 28 MiB`！**
   - 进一步查 `Win32_DeviceMemoryAddress` 物理 MMIO 地址段证实：`Core Ultra 9 285H` 主板 BIOS 给这张外置 OCuLink RTX 5090 分配的物理 MMIO 段**只有两段**：
     - `0x0000000080000000 - 0x00000000840FFFFF`（`65 MB`，BAR0 控制寄存器 + ROM）
     - **`0x0000004800000000 - 0x0000004801FFFFFF`（仅 `32 MB`！！这就是真实的物理 BAR1 窗口！）**
   - 换言之：绝大多数掌机/迷你主机的外置 OCuLink / USB4 口**不仅没开 32GB ReBAR，连传统台式机的 256MB BAR1 都没有，只有区区 `32 MB` 物理 BAR1（扣除系统占用只剩 `28 MB`）**！而与此同时，5090 板载的 `32 GB GDDR7`（`D3D12_HEAP_TYPE_DEFAULT = 1`）有足足 **29 GB 空闲显存** 躺着没法被 CPU 直接 BAR 映射，只能靠 GPU DMA（`CopyBufferRegion` / `CopyResource`）高速搬运！
4. 我们此前在任丘笔记本上对 `PBZ.exe` 静态反汇编的底稿已归档在 `/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/egpu-pbz-audit-20261113/pbz_static_audit.md`（证实 `PBZ` 三大动态上传池全部硬编码 `D3D12_HEAP_TYPE_UPLOAD = 2` 系统内存）；本机可参考 `/home/lmxxf/work/dlss5-default-swap/` 中成熟的 MinGW `dxgi.dll` 交叉编译写法，本机已有 `/usr/bin/x86_64-w64-mingw32-g++`。

---

## 本阶段交付目标（全部放在 `/home/lmxxf/work/egpu-dx12-booster/` 下）

请不要过度打磨，干净利落写出并交叉编译通过以下两个 64 位 Windows 产物（静态链接 libgcc/libstdc++，零额外运行时 DLL 依赖）：

### 产物 1：`/home/lmxxf/work/egpu-dx12-booster/build/d3d12_egpu_probe.exe`（无头命令行真机物理探针，无需桌面窗口即可通过 `ssh rtx5090` 直接跑！）
1. 枚举 DXGI Adapter，选中 `RTX 5090`（支持 `--adapter <substr>` 可选参数），创建 `ID3D12Device`；
2. 打印完整硬件与 D3D12 特性账本（JSON + 易读文本双输出或清晰结构化输出）：
   - Adapter 名称、DedicatedVideoMemory、SharedSystemMemory；
   - `IDXGIAdapter3::QueryVideoMemoryInfo`（`DXGI_MEMORY_SEGMENT_GROUP_LOCAL` 与 `NON_LOCAL` 的 Budget / CurrentUsage / AvailableForReservation）；
   - `CheckFeatureSupport`：`ARCHITECTURE1`（`UMA`, `CacheCoherentUMA`）、`D3D12_OPTIONS`、`D3D12_OPTIONS16`（`GPUUploadHeapSupported`, `DynamicResourcesSupported`）；
3. **BAR1 / CPU-visible VRAM 实弹探测**：
   - 分别测试 `D3D12_HEAP_TYPE_GPU_UPLOAD (5)`（若支持）和 `D3D12_HEAP_TYPE_CUSTOM`（`WRITE_COMBINE` + `MEMORY_POOL_L1`）在 `4 MB, 16 MB, 24 MB, 32 MB, 64 MB, 256 MB` 尺寸下的 `CreateCommittedResource` + `Map()` 是否成功、耗时多少，以及创建前后的 `QueryVideoMemoryInfo` 变化（验证超过 28MB BAR1 时是报错失败、还是被 WDDM 偷偷降级到系统内存 L0、还是触发分页抖动！）；
4. **OCuLink Gen4 x4 跨总线「多 Pass 倒吸 vs Shadow-Default 单次 DMA」微基准实测**：
   - 预编译一段极简 Compute Shader（可用 `d3dcompiler_47` 在运行时 `D3DCompile` 编译 HLSL 字符串，避免离线 DXC 依赖！），功能是每个线程按步长完整读取一个 `32 MB`（`8,388,608` 个 `uint`）的 `StructuredBuffer<uint>` / `ByteAddressBuffer` 并将异或和写入一个极小的 `DEFAULT` 输出槽防止编译器优化掉读取；
   - 测试当单帧内有 `K` 个独立 Pass（测 `K = 1, 4, 8`，每个 Pass 之间插 UAV Barrier 模拟 Shadow -> Prepass -> BasePass -> Lumen 多阶段重复读取同一帧动态常量/几何页，或测 `64 MB × 4 Pass = 256 MB`）时的真实 GPU 执行时间（用 `ID3D12QueryHeap` `TIMESTAMP` 精确测量）与端到端帧耗时（20 次迭代取中位数与 P95）：
     - **Case 1 (`Direct-UPLOAD`)**：`32 MB` 缓冲建在 `D3D12_HEAP_TYPE_UPLOAD (2)`，每帧 CPU `memcpy` 写满 32MB，然后 GPU `K` 个 Pass **直接绑 `UPLOAD` 缓冲的 SRV 跨 OCuLink 读取**；
     - **Case 2 (`Shadow-Default`)**：`32 MB` 写入缓冲建在 `UPLOAD (2)` + 伴生一块 `32 MB` 本地 `DEFAULT (1)` 缓冲；每帧 CPU `memcpy` 写满 `UPLOAD`，CommandList 开头执行 **1 次 `CopyBufferRegion`** 搬进 `DEFAULT (1)`（插 Copy->SRV Barrier），随后 GPU `K` 个 Pass **全部读取本地 `DEFAULT (1)` GDDR7 显存**；
     - **Case 3 (`Custom-L1 / GPU_UPLOAD`)**：若 32MB 或 16MB L1 创建成功，对比 CPU WC 跨线直写 `L1` 的 CPU `memcpy` 毫秒数 + GPU `K` 个 Pass 读取毫秒数；
5. **跨线同步往返延迟探针（Readback / Fence Latency）**：
   - 测量单次空/极小负载 `ExecuteCommandLists` + `CopyBufferRegion(64B -> READBACK)` + `Fence SetEventOnCompletion` 同步等待的往返延迟（跑 100 次取中位数微秒数），量化 OCuLink x4 的同步 Stall 单价。

### 产物 2：`/home/lmxxf/work/egpu-dx12-booster/build/dxgi.dll`（`eGPU-DX12-Booster v0.1` 轻量诊断遥测代理 DLL）
1. 标准 `dxgi.dll` 系统转发代理（转发 `C:\Windows\System32\dxgi.dll` 导出，同时拦截或通过 `GetProcAddress` / IAT / 同进程 `d3d12.dll` Hook `D3D12CreateDevice` 与 `CreateDXGIFactory*` SwapChain `Present`；参考 `dlss5-default-swap` 里已验证稳健的 Hook 方式，确保兼容 UE5 `PBZ.exe` 与 `b1-Win64-Shipping.exe`）；
2. 读取游戏同目录 `egpu_booster.ini`（不存在时默认走纯观测 `mode=0`，日志输出到同目录 `egpu_booster.log`）；
3. **精准捕获每帧 PCIe 病因遥测（开销极低，用原子计数或轻量表，不拖慢渲染线程）**：
   - 记录所有创建的 `ID3D12Heap` 与 Committed/Placed Buffer 资源，维护区间树/排序表 `[GPUVA_Start, GPUVA_End) -> {HeapType, Size, ResourcePtr}`；
   - 在 `ID3D12GraphicsCommandList` 上统计每帧：
     - `SetGraphicsRootConstantBufferView` / `SetComputeRootConstantBufferView` / `SetGraphicsRootShaderResourceView` / `SetComputeRootShaderResourceView` / `IASetVertexBuffers` / `IASetIndexBuffer` 中，**传入的 `GPUVirtualAddress` 落在 `UPLOAD (2)` 堆区间的次数与涉及的唯一/累计池字节数**（直接实锤游戏是不是让 GPU 跨 PCIe 反复直吸 `UPLOAD` 内存！）；
     - `CopyBufferRegion` / `CopyResource` / `CopyTextureRegion` 中，源为 `UPLOAD (2)` -> 目标为 `DEFAULT (1)` 的每帧拷贝次数与总字节数，以及源为 `DEFAULT (1)` -> 目标为 `READBACK (3)` 的每帧读回次数与总字节数；
     - `ResolveQueryData` 调用次数与目标堆类型（看遮挡查询是不是直接 Resolve 到 `READBACK` 堆）；
   - 在 `ID3D12CommandQueue::ExecuteCommandLists` 与 `ID3D12Fence::SetEventOnCompletion` / `GetCompletedValue`（或 `Present`）统计每帧 CommandList 提交次数、FPS、帧时间中位数/P99；
   - 每 120 帧（或每 2 秒）向 `egpu_booster.log` 刷新一段一目了然的统计快照！

### 验证要求
- 编译完成后，请**只将 `d3d12_egpu_probe.exe` 上传到 `rtx5090` 的临时目录 `C:\Temp\egpu_probe\` 运行一次**（不要动任何游戏目录！游戏目录留给我们确认后再测），把 `d3d12_egpu_probe.exe` 在 `rtx5090` 上的完整实测输出写进 `/home/lmxxf/work/egpu-dx12-booster/docs/probe_rtx5090_results.md` 并汇报！
