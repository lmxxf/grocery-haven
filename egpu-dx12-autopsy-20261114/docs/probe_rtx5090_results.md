# RTX 5090 Phase 1 实测报告

日期：2026-11-13（Asia/Taipei）。主机：`rtx5090` / `NucBox_EVO-T1`。执行目录：`C:\Temp\egpu_probe\`。

## 结论

- 探针执行一次，退出码 0，`completed=1`；18 组微基准的全部 65,536 个输出槽都通过 CPU 对照校验（每组计时后校验最后一轮）。
- `GPUUploadHeapSupported=1`。GPU_UPLOAD 与 CUSTOM（WRITE_COMBINE + L1）在 4/16/24/32/64/256 MiB 上均创建、Map、整块写入成功；每次释放后再测下一个尺寸，**不是同时占用容量测试**。
- 256 MiB 分配时，本进程 local usage 从 16,449,536 增至 284,884,992 字节，增量正好 268,435,456；nonlocal usage 保持 7,946,240。CPU 可见 L1 路线在这台机器上可用，不能继续沿用“物理 BAR 只有 32MB，所以 GPU_UPLOAD 不可用”的结论。
- 32 MiB × 8 Pass：Direct-UPLOAD GPU 中位耗时 44.1790 ms，Shadow-Default 5.1014 ms（含一次 DMA 及状态切换），约 **8.66 倍 GPU 阶段差距**；端到端分别 47.7830 / 9.7660 ms，约 **4.89 倍**。
- GPU_UPLOAD 同组 CPU 写入中位耗时 6.3640 ms，GPU 0.1498 ms，端到端 7.0340 ms。CPU 跨总线写入有成本，但后续本地反复读取明显便宜。
- 64B Copy → READBACK → Fence event 往返（100 次）：中位数 85 µs，P95 160 µs。
- 这证明指定微基准中的重复 UPLOAD 读取代价与两种替代路线收益，**没有证明某款游戏的瓶颈，也没有测到游戏帧率收益**。

## 目标机器与执行范围

`nvidia-smi` 只读查询：

```text
name, driver_version, pci.bus_id, pcie.link.gen.current, pcie.link.gen.max, pcie.link.width.current, pcie.link.width.max, memory.total [MiB]
NVIDIA GeForce RTX 5090, 621.14, 00000000:01:00.0, 2, 4, 4, 16, 32607 MiB
```

这是探针结束后的链路快照（空闲 Gen2、宽 x4）；没有同步记录计时阶段的链路频率。max width=16 是设备所报上限，不能写成当前协商宽度。DXGI 枚举中还包含 Intel Arc 140T 和软件适配器，实际选中 RTX 5090。

远端只上传 `d3d12_egpu_probe.exe`，命令为：

```bat
C:\Temp\egpu_probe\d3d12_egpu_probe.exe > C:\Temp\egpu_probe\probe_results.txt 2>&1
```

未写任何游戏目录；未上传或运行 `dxgi.dll`。实测 EXE 已从远端取回作为最终 `build/d3d12_egpu_probe.exe`，保证交付的是同一实测产物。

## 方法与统计口径

- D3DCompile 将内嵌 HLSL 编译为 cs_5_1。65,536 个线程按步长遍历全部输入 uint，每轮写各自的 XOR 输出（输出槽合计 256 KiB），防止输入读取被优化掉。每 Pass 之间有 UAV barrier。
- 每组 3 次预热 + 20 次计时；CPU 每轮 memcpy 全部输入。Direct 和 Shadow 使用相同大小、同一内容；Shadow 每轮只复制一次，随后 K 次读取本地 DEFAULT。
- GPU 时间由同一 DIRECT queue 的 TIMESTAMP query 计算；Shadow 包含 DMA、资源状态切换及全部 dispatch。CPU 写入时间单独计量；端到端包含 memcpy、命令录制、提交与 fence event 等待，不包含结果检查。
- 中位数及 P95 使用排序后索引 `ceil((N-1)*p)` 的上侧经验分位数。20 次样本的 P95 因此为最大样本；与线性插值/nearest-rank 的 P95 算法略有不同。
- 写相同输入后，末轮以不同 salt 验证所有输出；没有使用 PIX 或硬件 PCIe 流量计数器。重复读取允许命中 GPU cache，不等同于每个 Pass 都读取 GDDR7。
- 分配阶段的单次 CPU 首写可能包含页映射/冷启动成本；不能直接拿它与预热后的 memcpy 中位数对比。CPU 写入计时未单独分离 WC 排空，端到端计时及 GPU 输出校验覆盖提交完成。

## 微基准全部结果

单位 ms。以下每组 20 次计时，校验错误均为 0。

| 路线 | MiB | Pass | CPU 中位 | CPU P95 | GPU 中位 | GPU P95 | 端到端中位 | 端到端 P95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Direct-UPLOAD | 32 | 1 | 2.5600 | 3.2860 | 5.2646 | 5.2929 | 8.4490 | 8.9360 |
| Direct-UPLOAD | 32 | 4 | 2.5850 | 4.1130 | 22.0023 | 22.2123 | 25.5170 | 26.8520 |
| Direct-UPLOAD | 32 | 8 | 2.3960 | 3.5910 | 44.1790 | 45.6664 | 47.7830 | 48.8020 |
| Shadow-Default | 32 | 1 | 3.7020 | 6.9300 | 4.9430 | 6.2574 | 9.5430 | 12.7320 |
| Shadow-Default | 32 | 4 | 3.5010 | 5.0320 | 4.9972 | 5.9332 | 9.7490 | 10.7080 |
| Shadow-Default | 32 | 8 | 3.7220 | 4.9340 | 5.1014 | 5.9157 | 9.7660 | 11.0240 |
| GPU_UPLOAD | 32 | 1 | 6.2390 | 6.9990 | 0.0205 | 0.0473 | 6.8730 | 7.7100 |
| GPU_UPLOAD | 32 | 4 | 6.2360 | 7.5500 | 0.0764 | 0.1041 | 6.9710 | 8.2690 |
| GPU_UPLOAD | 32 | 8 | 6.3640 | 6.7160 | 0.1498 | 0.1774 | 7.0340 | 7.6260 |
| GPU_UPLOAD | 16 | 1 | 3.0560 | 3.6120 | 0.0098 | 0.0406 | 3.7190 | 4.3910 |
| GPU_UPLOAD | 16 | 4 | 3.1320 | 4.4130 | 0.0396 | 0.0534 | 3.7140 | 4.7440 |
| GPU_UPLOAD | 16 | 8 | 3.1690 | 4.6030 | 0.0976 | 1.0240 | 3.8100 | 5.0490 |
| Custom-L1 | 32 | 1 | 6.3270 | 7.3560 | 0.0401 | 0.1128 | 6.7980 | 7.9310 |
| Custom-L1 | 32 | 4 | 6.0650 | 6.7230 | 0.0987 | 0.1311 | 6.7810 | 7.4750 |
| Custom-L1 | 32 | 8 | 6.4160 | 7.4440 | 0.1934 | 0.2045 | 7.1350 | 8.2930 |
| Custom-L1 | 16 | 1 | 3.0640 | 4.0870 | 0.0272 | 0.0328 | 3.5290 | 4.5350 |
| Custom-L1 | 16 | 4 | 3.0290 | 3.7430 | 0.0571 | 0.0652 | 3.6140 | 4.2040 |
| Custom-L1 | 16 | 8 | 3.0980 | 3.5060 | 0.0982 | 0.1055 | 3.7270 | 4.2070 |

## BAR 与特性解释

`QueryVideoMemoryInfo` 是进程分段预算/记账信息，不能独自确定物理 BAR 窗口、每页实际驻留或是否有 WDDM 重映射。分配、Map 和写入成功以及 local usage 增长足以否定“28MB 是本进程可创建的硬上限”，不足以反推出真实物理 BAR 大小。先前基于两段 WMI MMIO 地址的判断应重新核验，不能当作已证实的容量限制。

`OPTIONS16` 的两个字段是 `DynamicDepthBiasSupported` 与 `GPUUploadHeapSupported`，没有任务书中的 `DynamicResourcesSupported`。本机旧 MinGW SDK 未声明 OPTIONS16，探针按官方 ABI 使用 feature=45、两个 BOOL。参考：[Microsoft DirectX-Headers](https://github.com/microsoft/DirectX-Headers/blob/main/include/directx/d3d12.h)、[Microsoft GPU Upload Heaps 规范](https://microsoft.github.io/DirectX-Specs/d3d/D3D12GPUUploadHeaps.html)。

## v0.1 DLL 验证范围

64 位交叉编译通过；全部 20 个 DXGI 导出及 ordinal 与取回的目标系统 DLL 对齐，转发 thunk 保留 Win64 参数寄存器与栈参数；Device4/8/9/10 方法槽位与官方头文件核对。静态 C++ 运行时，导入仅 Windows 系统 DLL。检查脚本：`python3 scripts/check_artifacts.py`。

遵照本阶段“只上传 EXE”的要求，**DLL 未运行验证**，尚不声明 UE5、Denuvo 或某款游戏兼容；运行时稳定性、计数正确性及开销留待后续独立 smoke test 和游戏实测。遥测的遗漏与计数语义详见 README。

产物指纹：

```json
{
  "passed": true,
  "artifacts": [
    {
      "file": "d3d12_egpu_probe.exe",
      "bytes": 582149,
      "sha256": "28446699a174f5d1b5fb491da2eb0a21116c216b5bcd59a7bf13b8bcddff0b5c",
      "imports": [
        "d3d12.dll",
        "D3DCOMPILER_47.dll",
        "dxgi.dll",
        "KERNEL32.dll",
        "msvcrt.dll"
      ]
    },
    {
      "file": "dxgi.dll",
      "bytes": 575422,
      "sha256": "ccbb5f01afb0378e7d9df6d9289ffa5a3503d8e2b30ea553518c5c7f3d7d5940",
      "imports": [
        "KERNEL32.dll",
        "msvcrt.dll",
        "ole32.dll"
      ]
    }
  ]
}
```

## 完整原始输出

同内容另存 `build/probe_rtx5090_raw.txt`，远端保留 `C:\Temp\egpu_probe\probe_results.txt`。以下未删节：

```text
adapter index=0 name=NVIDIA GeForce RTX 5090 dedicated=33750515712 shared=51028144128 vendor=10de device=2b85
adapter index=1 name=Intel(R) Arc(TM) 140T GPU (32GB) dedicated=134217728 shared=51028144128 vendor=8086 device=7d51
adapter index=2 name=Microsoft Basic Render Driver dedicated=0 shared=51028144128 vendor=1414 device=008c
architecture1 hr=00000000 UMA=0 coherentUMA=0 tile_based=0 isolatedMMU=1
options hr=00000000 double=1 logicop=1 minprecision=2 tiled=4 binding=3 stencilref=0 typedUAV=1 ROV=1 conservative=3 gpuVA_bits=40 swizzle=0 crossnode=0 crossadapter=0 VP_RT=1 heapTier=2
options16 hr=00000000 dynamicDepthBias=1 GPUUploadHeapSupported=1 (DynamicResourcesSupported is not an OPTIONS16 field)
budget tag=initial segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=initial segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=4 create_hr=00000000 map_hr=00000000 create_ms=0.9520 map_ms=1.2280 write_ms=3.4500
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=20643840 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=16 create_hr=00000000 map_hr=00000000 create_ms=2.0140 map_ms=1.3590 write_ms=13.2900
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=33226752 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=24 create_hr=00000000 map_hr=00000000 create_ms=1.3070 map_ms=1.8490 write_ms=19.2960
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=41615360 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=32 create_hr=00000000 map_hr=00000000 create_ms=1.5010 map_ms=2.2000 write_ms=24.9820
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=50003968 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=64 create_hr=00000000 map_hr=00000000 create_ms=3.1260 map_ms=9.5270 write_ms=51.6160
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=83558400 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=256 create_hr=00000000 map_hr=00000000 create_ms=7.1650 map_ms=30.6850 write_ms=207.9420
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=284884992 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=4 create_hr=00000000 map_hr=00000000 create_ms=0.6250 map_ms=1.0020 write_ms=0.9360
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=20643840 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=16 create_hr=00000000 map_hr=00000000 create_ms=0.6410 map_ms=1.1390 write_ms=2.9970
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=33226752 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=24 create_hr=00000000 map_hr=00000000 create_ms=1.1520 map_ms=1.7670 write_ms=4.4390
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=41615360 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=32 create_hr=00000000 map_hr=00000000 create_ms=1.1230 map_ms=1.7650 write_ms=5.8980
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=50003968 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=64 create_hr=00000000 map_hr=00000000 create_ms=2.2900 map_ms=6.4510 write_ms=12.4190
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=83558400 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=256 create_hr=00000000 map_hr=00000000 create_ms=5.8190 map_ms=23.8020 write_ms=48.7170
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=284884992 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
benchmark case=Direct-UPLOAD MB=32 K=1 samples=20 warmup=3 cpu_median_ms=2.5600 cpu_p95_ms=3.2860 gpu_median_ms=5.2646 gpu_p95_ms=5.2929 e2e_median_ms=8.4490 e2e_p95_ms=8.9360 validation_bad=0
benchmark case=Direct-UPLOAD MB=32 K=4 samples=20 warmup=3 cpu_median_ms=2.5850 cpu_p95_ms=4.1130 gpu_median_ms=22.0023 gpu_p95_ms=22.2123 e2e_median_ms=25.5170 e2e_p95_ms=26.8520 validation_bad=0
benchmark case=Direct-UPLOAD MB=32 K=8 samples=20 warmup=3 cpu_median_ms=2.3960 cpu_p95_ms=3.5910 gpu_median_ms=44.1790 gpu_p95_ms=45.6664 e2e_median_ms=47.7830 e2e_p95_ms=48.8020 validation_bad=0
benchmark case=Shadow-Default MB=32 K=1 samples=20 warmup=3 cpu_median_ms=3.7020 cpu_p95_ms=6.9300 gpu_median_ms=4.9430 gpu_p95_ms=6.2574 e2e_median_ms=9.5430 e2e_p95_ms=12.7320 validation_bad=0
benchmark case=Shadow-Default MB=32 K=4 samples=20 warmup=3 cpu_median_ms=3.5010 cpu_p95_ms=5.0320 gpu_median_ms=4.9972 gpu_p95_ms=5.9332 e2e_median_ms=9.7490 e2e_p95_ms=10.7080 validation_bad=0
benchmark case=Shadow-Default MB=32 K=8 samples=20 warmup=3 cpu_median_ms=3.7220 cpu_p95_ms=4.9340 gpu_median_ms=5.1014 gpu_p95_ms=5.9157 e2e_median_ms=9.7660 e2e_p95_ms=11.0240 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=1 samples=20 warmup=3 cpu_median_ms=6.2390 cpu_p95_ms=6.9990 gpu_median_ms=0.0205 gpu_p95_ms=0.0473 e2e_median_ms=6.8730 e2e_p95_ms=7.7100 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.2360 cpu_p95_ms=7.5500 gpu_median_ms=0.0764 gpu_p95_ms=0.1041 e2e_median_ms=6.9710 e2e_p95_ms=8.2690 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=8 samples=20 warmup=3 cpu_median_ms=6.3640 cpu_p95_ms=6.7160 gpu_median_ms=0.1498 gpu_p95_ms=0.1774 e2e_median_ms=7.0340 e2e_p95_ms=7.6260 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=1 samples=20 warmup=3 cpu_median_ms=3.0560 cpu_p95_ms=3.6120 gpu_median_ms=0.0098 gpu_p95_ms=0.0406 e2e_median_ms=3.7190 e2e_p95_ms=4.3910 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=4 samples=20 warmup=3 cpu_median_ms=3.1320 cpu_p95_ms=4.4130 gpu_median_ms=0.0396 gpu_p95_ms=0.0534 e2e_median_ms=3.7140 e2e_p95_ms=4.7440 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=8 samples=20 warmup=3 cpu_median_ms=3.1690 cpu_p95_ms=4.6030 gpu_median_ms=0.0976 gpu_p95_ms=1.0240 e2e_median_ms=3.8100 e2e_p95_ms=5.0490 validation_bad=0
benchmark case=Custom-L1 MB=32 K=1 samples=20 warmup=3 cpu_median_ms=6.3270 cpu_p95_ms=7.3560 gpu_median_ms=0.0401 gpu_p95_ms=0.1128 e2e_median_ms=6.7980 e2e_p95_ms=7.9310 validation_bad=0
benchmark case=Custom-L1 MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.0650 cpu_p95_ms=6.7230 gpu_median_ms=0.0987 gpu_p95_ms=0.1311 e2e_median_ms=6.7810 e2e_p95_ms=7.4750 validation_bad=0
benchmark case=Custom-L1 MB=32 K=8 samples=20 warmup=3 cpu_median_ms=6.4160 cpu_p95_ms=7.4440 gpu_median_ms=0.1934 gpu_p95_ms=0.2045 e2e_median_ms=7.1350 e2e_p95_ms=8.2930 validation_bad=0
benchmark case=Custom-L1 MB=16 K=1 samples=20 warmup=3 cpu_median_ms=3.0640 cpu_p95_ms=4.0870 gpu_median_ms=0.0272 gpu_p95_ms=0.0328 e2e_median_ms=3.5290 e2e_p95_ms=4.5350 validation_bad=0
benchmark case=Custom-L1 MB=16 K=4 samples=20 warmup=3 cpu_median_ms=3.0290 cpu_p95_ms=3.7430 gpu_median_ms=0.0571 gpu_p95_ms=0.0652 e2e_median_ms=3.6140 e2e_p95_ms=4.2040 validation_bad=0
benchmark case=Custom-L1 MB=16 K=8 samples=20 warmup=3 cpu_median_ms=3.0980 cpu_p95_ms=3.5060 gpu_median_ms=0.0982 gpu_p95_ms=0.1055 e2e_median_ms=3.7270 e2e_p95_ms=4.2070 validation_bad=0
roundtrip samples=100 median_us=85.000 p95_us=160.000
budget tag=final segment=local hr=0x00000000 budget=32945209344 usage=22093824 reservation_available=16606822400 reservation=0
budget tag=final segment=nonlocal hr=0x00000000 budget=50222837760 usage=27918336 reservation_available=25245636608 reservation=0
completed=1 caveat=allocation_and_budget_do_not_prove_physical_BAR_size_or_residency; repeated_reads_may_hit_GPU_cache
```
