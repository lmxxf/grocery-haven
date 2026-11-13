# eGPU-DX12-Booster · Phase 2 任务书（给闇 `wC:p1`：实装 `Mode=1 GPU_UPLOAD` 加速 + 补齐 Descriptor 遥测 + 无头自检）

Phase 1 干得非常漂亮！`d3d12_egpu_probe.exe` 在 `rtx5090` 真机上跑出了决定性铁证：
1. `GPUUploadHeapSupported = 1`，且 `GPU_UPLOAD (5)` 与 `Custom-L1` 在 `4 MB ~ 256 MB` 全尺寸创建+映射 100% 成功（推翻了此前 WMI 32-bit 截断造成的 28MB 硬上限假象）；
2. `32 MiB × 8 Pass` 下：
   - `Direct-UPLOAD (Type=2)`：GPU 中位耗时 **`44.18 ms`**（端到端 `47.78 ms`）
   - `Shadow-Default`：GPU 中位耗时 **`5.10 ms`**（端到端 `9.77 ms`，GPU 快 **8.66 倍**）
   - **`GPU_UPLOAD (Type=5)`：GPU 中位耗时仅 `0.15 ms`**（端到端 `7.03 ms`，**GPU 阶段快 295 倍**！）
3. 64B Readback + Fence 同步往返中位数仅 **`85 µs`**。

现在进入 **Phase 2**：把 `/home/lmxxf/work/egpu-dx12-booster/build/dxgi.dll` 升级为 **v0.2 实战可加速版**，并在 `rtx5090` 的 `C:\Temp\egpu_probe\` 下做一次真机无头注入自检（依然暂不动任何游戏目录）。

---

## 具体升级要求

### 1. 补齐 UE5 Descriptor Heap 路径的 `UPLOAD` 绑定遥测
在 v0.1 中只统计了 Root CBV/SRV 和 VBV/IBV，但 UE5 大量动态 Uniform/Structured Buffer 是通过 `ID3D12Device::CreateConstantBufferView`（slot 17）和 `ID3D12Device::CreateShaderResourceView`（slot 18）写入 Descriptor Heap 后再 `SetGraphicsRootDescriptorTable` 绑定的：
- 请同时 Hook `ID3D12Device`（及 `Device4/8/9/10` 对应 vtable）的：
  - `CreateConstantBufferView`（slot 17）：检查 `pDesc->BufferLocation` 是否落在 `UPLOAD (2)`（或被提拔的 `GPU_UPLOAD`）区间；
  - `CreateShaderResourceView`（slot 18）：当传入 `pResource` 为 Buffer 时，统计其堆类型是否为 `UPLOAD (2)`（或被提拔池）；
  - `ID3D12Resource::Map`（slot 8）：统计 `UPLOAD` 与被提拔 `GPU_UPLOAD` 资源的 `Map` 次数，以及 `pReadRange != nullptr && pReadRange->End > pReadRange->Begin`（显式声明 CPU 读取）的次数！

### 2. 实装 `mode=1`：安全可控的 `UPLOAD (2) -> GPU_UPLOAD (5)` 自动提拔引擎
当 `egpu_booster.ini` 中 `[booster] mode=1`（且检查设备 `OPTIONS16.GPUUploadHeapSupported == TRUE`）时：
1. **同时覆盖 Committed 与 Placed 两条路径（极其关键！我们在 `PBZ.exe` 反汇编中实锤了 `Small Block (4MB)` 与 `Big Block (32MB)` 是池化分配器，可能走 `CreateHeap` + `CreatePlacedResource` 或大块 `CreateCommittedResource`）**：
   - **路径 A（`CreateCommittedResource` / `1` / `2` / `3`）**：当 `pHeapProperties->Type == D3D12_HEAP_TYPE_UPLOAD` 且资源为 **Buffer**（`Dimension == D3D12_RESOURCE_DIMENSION_BUFFER`），且尺寸落在 `[min_buffer_kb, max_buffer_mb]` 范围内，且当前在途提拔总量 `promoted_live_bytes + width <= max_total_mb` 时：
     - 构造局部副本 `D3D12_HEAP_PROPERTIES promotedProps = *pHeapProperties; promotedProps.Type = (D3D12_HEAP_TYPE)5;`（即 `D3D12_HEAP_TYPE_GPU_UPLOAD`）；
     - 先尝试用 `promotedProps` 调用原始 `CreateCommittedResource*`；
     - **零崩溃兜底（Fallback）**：若返回 `FAILED(hr)`，立即用原始 `pHeapProperties`（`UPLOAD=2`）重试调用并计数 `promote_fallbacks++`，绝不让游戏因某个特殊 Flag 崩溃！
   - **路径 B（`CreateHeap` / `CreateHeap1`）**：当 `pDesc->Properties.Type == D3D12_HEAP_TYPE_UPLOAD`，且不包含禁止 Buffer 的 Flag（例如包含 `ALLOW_ONLY_NON_RT_DS_TEXTURES` 或 `ALLOW_ONLY_RT_DS_TEXTURES` 时跳过，只提拔允许 Buffer 的堆），且 `SizeInBytes` 落在 `[min_heap_kb, max_heap_mb]` 范围内，且未超 `max_total_mb` 总配额时：
     - 尝试将副本 `Properties.Type` 改为 `5`（`D3D12_HEAP_TYPE_GPU_UPLOAD`）调用原始 `CreateHeap*`；若 `FAILED(hr)` 无缝 Fallback 回原始 `UPLOAD=2`！
     - 当资源或 Heap 最终 `Release()` 归零销毁时，精确扣减 `promoted_live_bytes` 配额！
2. **INI 可调参数（带合理默认值）**：
   ```ini
   [booster]
   enabled=1
   ; 0 = pure telemetry, 1 = promote eligible UPLOAD buffers/heaps to GPU_UPLOAD (ReBAR)
   mode=0
   min_buffer_kb=4
   max_buffer_mb=64
   min_heap_kb=64
   max_heap_mb=128
   max_total_mb=1024
   spoof_heap_properties=0
   ```
   - 若 `spoof_heap_properties=1`：在被提拔的 Resource `GetHeapProperties`（slot 11）和 Heap `GetDesc`（slot 7）上把返回的 `Type` 伪装回 `D3D12_HEAP_TYPE_UPLOAD (2)`（以防引擎内部 `check(HeapType == UPLOAD)` 断言；默认 0，留作开关备用）。
3. **快照日志新增字段**：
   - 在 `snapshot`（以及没有 SwapChain Present 时的 `worker` 2 秒定时快照——注意！无 SwapChain 的命令行程序如 `d3d12_egpu_probe.exe` 没有 `Present`，当 `submits > 0` 且距上次超过 2 秒时也输出快照，并在进程退出/卸载前尽量刷一次日志）中清晰打印：
     `mode`, `gpu_upload_supported`, `promoted_heaps`, `promoted_buffers`, `promoted_live_mb`, `promote_fallbacks`, `cbv_upload_creates`, `srv_upload_creates`, `root_upload_binds`, `map_calls`, `map_explicit_reads`。

### 3. 在 `rtx5090` 的 `C:\Temp\egpu_probe\` 上做真机端到端闭环验证！
不用碰游戏目录，直接在 `C:\Temp\egpu_probe\` 下把 `dxgi.dll` + `egpu_booster.ini` 跟 `d3d12_egpu_probe.exe` 放一起跑两次对照测试（确保 `d3d12_egpu_probe.exe` 会加载同目录 `dxgi.dll` 创建 Factory 枚举 Adapter，从而真实触发 `dxgi.dll` 的全套 IAT Hook、vtable Hook、遥测和 `mode=1` 提拔逻辑！）：
1. **`mode=0` 运行 `d3d12_egpu_probe.exe`**：验证 `egpu_booster.log` 正常生成，`Direct-UPLOAD` 32MB × 8 Pass 依然是 `~44 ms`，遥测准确抓到了 `UPLOAD` 创建、SRV 创建、Map 和拷贝计数，零 `hook_failures`；
2. **`mode=1` 运行 `d3d12_egpu_probe.exe`**：验证原本探针里写死的 `Direct-UPLOAD`（`HeapType=2`，32MB × 8 Pass）在**不改探针一行代码**的情况下，被同目录 `dxgi.dll` 透明偷梁换柱成了 `GPU_UPLOAD (5)`，**`Direct-UPLOAD` 的 GPU 耗时直接从 `~44 ms` 暴跌到 `~0.15 ms`（端到端从 `~48 ms` 暴跌到 `~7 ms`），且全部 65,536 个 XOR 计算校验 100% 通过（`validation_bad=0`）**！

把验证结果写入 `/home/lmxxf/work/egpu-dx12-booster/docs/phase2_smoke_results.md` 并汇报！别过度打磨，稳准狠拿下！
