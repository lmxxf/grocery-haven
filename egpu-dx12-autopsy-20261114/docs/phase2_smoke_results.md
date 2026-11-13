# Phase 2 · v0.2 RTX 5090 真机闭环报告

日期：2026-11-13。主机：`rtx5090` / `NucBox_EVO-T1`，RTX 5090，驱动 621.14。全部部署、日志和测试均在 `C:\Temp\egpu_probe\`，游戏目录零改动。

## 核心结论

**不修改探针源码或 EXE，实际加载同目录 dxgi.dll，通过 mode=1 透明提拔，Direct-UPLOAD 32MiB × 8 Pass 的 GPU 中位耗时由 44.1682ms 降到 0.1534ms；端到端由 48.8730ms 降到 6.4600ms。**

GPU 阶段比值约 **287.93 倍**；端到端比值约 **7.57 倍**。这是指定重复读取微基准的结果，不能写成游戏帧率收益。

| mode | CPU memcpy 中位 ms | GPU 中位 ms | GPU P95 ms | 端到端中位 ms | 端到端 P95 ms |
|---:|---:|---:|---:|---:|---:|
| 0 | 2.9720 | 44.1682 | 45.2745 | 48.8730 | 49.5260 |
| 1 | 5.9440 | 0.1534 | 0.1799 | 6.4600 | 7.1990 |

两轮各 18 组微基准，全部 `validation_bad=0`，每组最后一轮 65,536 个输出槽逐一 CPU 对照；两轮退出码均为 0。计时口径沿用 Phase 1，3 次预热、20 次样本，上侧经验分位数。没有改测量代码来制造速度差。

mode=1 的日志：2 个 32MiB Committed Buffer 提拔成功，峰值在途提拔 32MiB，释放后 `promoted_live_bytes=0`；默认配置下 `promote_fallbacks=0`，所有快照 `hook_failures=0`。mode=0 未提拔。

## 遥测对账与补充自检

原探针只调用 Root SRV，不调用 CreateConstantBufferView/CreateShaderResourceView 或 CreateHeap/CreatePlacedResource。因此它的 CBV/SRV 创建数为零是预期行为，不能谎报为已经覆盖 Descriptor 路径；这部分由独立 `promoter_smoke.exe` 补测。

两轮探针的日志累计都精确对上工作负载：

- 532 次 CommandList 提交：414 次计时提交 + 18 次输出验证 + 100 次 64B 往返。
- 414 次 ResolveQueryData、69 次 upload→default 拷贝、18 次 default→readback 拷贝、24 个资源创建。
- mode=0：69 次 root_upload_binds、2 次 UPLOAD Map。
- mode=1：69 次 root_promoted_binds、2 次 promoted Map。
- 无 SwapChain：两秒定时日志正常；CRT exit 前最终快照正常落盘。

独立自检使用 8MiB 总配额，在 mode=0、mode=1、mode=1+spoof 三种配置下均退出 0：

| 检查 | 结果 |
|---|---|
| 基础 Committed + Heap + Placed | mode=0 返回 Type=2；mode=1 返回 Type=5；开启 spoof 返回 Type=2 |
| CBV/SRV 创建 | 每轮各 3 个；mode=1 为 2 个 promoted + 1 个配额阻挡后保留的 UPLOAD |
| Map | 每轮 6 次，其中 3 次显式非空读取范围；mode=1 为 4 次 promoted + 2 次普通 UPLOAD |
| 数据正确性 | 每轮三块 4MiB 数据经 GPU Copy 至 DEFAULT 再 READBACK，全量 memcmp 通过 |
| 配额上限 | 一块 4MiB Committed + 一块 4MiB Heap 占满，第三块保留 UPLOAD；峰值恰为 8MiB |
| 配额回收 | 释放 owning Buffer/Heap 后归零，之后的 4MiB 分配重新获准提拔；Placed 不双重计费 |
| 小尺寸门槛 | 1KiB Buffer 保持 UPLOAD |
| 版本化接口 | CommittedResource1/2/3、CreateHeap1、CreatePlacedResource1/2 均通过类型和生命周期检查 |
| 伪装 ABI | Resource.GetHeapProperties、Heap.GetDesc 的返回类型、大小及 GPUVA 均正确 |
| 真实驱动失败重试 | 共享相关标志触发 4 次 fallback；原始 UPLOAD 也拒绝，最终 HRESULT 与 mode=0 一致，无崩溃或配额泄漏 |

真实驱动的共享标志不能演示“fallback 后成功”。额外 `logic\promotion_fallback_test.exe` **直接调用生产 helper**，仅在测试 lambda 中注入 promoted E_OUTOFMEMORY，然后用原始 UPLOAD 参数真实创建 Buffer/Heap，两个成功兜底分支都通过；同时验证原始错误保留、零配额、不支持设备跳过及最终 live=0。这不是驱动自然故障，也未给生产 DLL 添加故障开关。

## 实现与边界

- `mode=1` 覆盖 Committed/1/2/3 与 Heap/1；Placed/1/2 继承实际堆类型与 promotion 状态。
- 配额用原子 CAS 预留，失败立即撤销；最终 Release 扣减 owning charge。有创建重入保护，避免 runtime 内部转调造成双重提拔。
- 新增 CBV/SRV 创建遥测、Map/显式读取遥测，保留已有绑定、拷贝、Resolve、Fence、Present 计数。
- 支持全部任务书 INI 项，缺配置默认 mode=0。测试结束后远端配置已恢复 mode=0。
- 更正任务书两处槽位：Resource.GetHeapProperties=14，Heap.GetDesc=8；不是 11/7。Heap.GetDesc 按 Win64 COM aggregate-return ABI 实现。
- 新自检的 Device10 Buffer 初始 layout 必须为 UNDEFINED；首轮自检曾误用 GENERIC_READ 被原始驱动拒绝，修正后全部通过。依据：[Microsoft CreateCommittedResource3 文档](https://learn.microsoft.com/en-us/windows/win32/api/d3d12/nf-d3d12-id3d12device10-createcommittedresource3)。正式性能对照使用最终 DLL 重新执行，两轮结果见本报告。
- Descriptor 创建数是创建时证据，没有追踪 descriptor-table 的实际执行；绑定池字节数不是 PCIe 流量。完整计数语义见 README。
- Fallback 仅在创建失败时重试，不能在后续 Map/CPU 读声明/游戏错误时自动迁回系统内存。用户的原始请求本身失败时，保留其 HRESULT。
- 尚未做任何游戏注入、Present 场景运行验证或游戏开销量化；不声明 UE5/Denuvo 已兼容。强制结束进程可能丢最后一段日志。

## 产物与复现

原探针 EXE SHA256 与 Phase 1 一致：

```text
28446699a174f5d1b5fb491da2eb0a21116c216b5bcd59a7bf13b8bcddff0b5c
```

最终 DLL SHA256（本地与远端一致）：

```text
f852b1d72b84bb1037993f2c99981ebc905b71d7d93433f03368e40b34c48f27
```

编译：`./build.sh --dll-only`；补充自检编译：`./scripts/build_smoke_tests.sh`。

远端测试脚本：`scripts/run_mode_smoke.ps1 -Mode 0/1`、`scripts/run_promoter_smoke.ps1`。隔离故障测试 EXE 必须放在不含代理 DLL 的 `logic` 子目录运行。

检查：`python3 scripts/check_artifacts.py`（x64、系统 DLL 依赖、20 个 DXGI 导出及 ordinal）；`python3 scripts/check_phase2_results.py`（全部输出/计数对账）。两项均通过。

全部最终原始结果位于 `build/phase2/`，包含每轮完整 probe stdout、stderr、exit、INI、遥测、自检和故障注入结果。探针 source SHA256：`94547217442630a4906d3beb886acd0cd44fa06c74abb2c76a4d0fb75ef1c3b7`。

## 完整实测日志

### mode0_probe.txt

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
allocation type=5 MB=4 create_hr=00000000 map_hr=00000000 create_ms=0.8890 map_ms=1.2710 write_ms=0.7390
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=20643840 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=16 create_hr=00000000 map_hr=00000000 create_ms=0.9600 map_ms=1.9270 write_ms=2.9770
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=33226752 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=24 create_hr=00000000 map_hr=00000000 create_ms=1.6200 map_ms=3.3100 write_ms=19.1850
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=41615360 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=32 create_hr=00000000 map_hr=00000000 create_ms=1.0980 map_ms=3.3150 write_ms=24.9490
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=50003968 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=64 create_hr=00000000 map_hr=00000000 create_ms=2.5100 map_ms=10.2890 write_ms=59.5690
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=83558400 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=256 create_hr=00000000 map_hr=00000000 create_ms=8.6070 map_ms=29.5180 write_ms=207.9230
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=284884992 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=4 create_hr=00000000 map_hr=00000000 create_ms=0.7620 map_ms=1.1720 write_ms=2.8950
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=20643840 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=16 create_hr=00000000 map_hr=00000000 create_ms=1.0590 map_ms=2.4990 write_ms=11.9560
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=33226752 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=24 create_hr=00000000 map_hr=00000000 create_ms=1.3710 map_ms=3.9940 write_ms=19.3820
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=41615360 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=32 create_hr=00000000 map_hr=00000000 create_ms=1.2590 map_ms=5.8130 write_ms=25.4390
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=50003968 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=64 create_hr=00000000 map_hr=00000000 create_ms=1.9800 map_ms=8.0950 write_ms=51.6970
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=83558400 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=256 create_hr=00000000 map_hr=00000000 create_ms=7.1190 map_ms=28.5000 write_ms=165.3430
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=284884992 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
benchmark case=Direct-UPLOAD MB=32 K=1 samples=20 warmup=3 cpu_median_ms=2.3620 cpu_p95_ms=2.7900 gpu_median_ms=5.2694 gpu_p95_ms=5.2975 e2e_median_ms=8.1070 e2e_p95_ms=8.7330 validation_bad=0
benchmark case=Direct-UPLOAD MB=32 K=4 samples=20 warmup=3 cpu_median_ms=2.6210 cpu_p95_ms=3.5040 gpu_median_ms=21.9765 gpu_p95_ms=22.2358 e2e_median_ms=25.5070 e2e_p95_ms=26.9500 validation_bad=0
benchmark case=Direct-UPLOAD MB=32 K=8 samples=20 warmup=3 cpu_median_ms=2.9720 cpu_p95_ms=4.2440 gpu_median_ms=44.1682 gpu_p95_ms=45.2745 e2e_median_ms=48.8730 e2e_p95_ms=49.5260 validation_bad=0
benchmark case=Shadow-Default MB=32 K=1 samples=20 warmup=3 cpu_median_ms=3.5470 cpu_p95_ms=5.7750 gpu_median_ms=4.9362 gpu_p95_ms=5.7670 e2e_median_ms=9.1870 e2e_p95_ms=11.3370 validation_bad=0
benchmark case=Shadow-Default MB=32 K=4 samples=20 warmup=3 cpu_median_ms=3.4980 cpu_p95_ms=4.7440 gpu_median_ms=4.9749 gpu_p95_ms=5.9333 e2e_median_ms=9.0300 e2e_p95_ms=10.4070 validation_bad=0
benchmark case=Shadow-Default MB=32 K=8 samples=20 warmup=3 cpu_median_ms=3.5810 cpu_p95_ms=4.6290 gpu_median_ms=5.0709 gpu_p95_ms=5.9981 e2e_median_ms=9.3570 e2e_p95_ms=10.2010 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=1 samples=20 warmup=3 cpu_median_ms=6.4740 cpu_p95_ms=7.7880 gpu_median_ms=0.0209 gpu_p95_ms=0.0831 e2e_median_ms=6.9540 e2e_p95_ms=8.3500 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.2410 cpu_p95_ms=6.8530 gpu_median_ms=0.0759 gpu_p95_ms=0.1042 e2e_median_ms=6.6210 e2e_p95_ms=7.4080 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=8 samples=20 warmup=3 cpu_median_ms=6.2100 cpu_p95_ms=9.1570 gpu_median_ms=0.1516 gpu_p95_ms=0.1775 e2e_median_ms=7.0500 e2e_p95_ms=10.8960 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=1 samples=20 warmup=3 cpu_median_ms=2.9950 cpu_p95_ms=3.6330 gpu_median_ms=0.0097 gpu_p95_ms=0.0237 e2e_median_ms=3.2870 e2e_p95_ms=4.2350 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=4 samples=20 warmup=3 cpu_median_ms=3.0000 cpu_p95_ms=3.5940 gpu_median_ms=0.0564 gpu_p95_ms=0.0660 e2e_median_ms=3.3890 e2e_p95_ms=4.1290 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=8 samples=20 warmup=3 cpu_median_ms=2.9770 cpu_p95_ms=3.7590 gpu_median_ms=0.0906 gpu_p95_ms=0.1012 e2e_median_ms=3.4140 e2e_p95_ms=4.2920 validation_bad=0
benchmark case=Custom-L1 MB=32 K=1 samples=20 warmup=3 cpu_median_ms=5.9960 cpu_p95_ms=7.0910 gpu_median_ms=0.0394 gpu_p95_ms=0.0682 e2e_median_ms=6.7350 e2e_p95_ms=8.6440 validation_bad=0
benchmark case=Custom-L1 MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.1530 cpu_p95_ms=10.9400 gpu_median_ms=0.1218 gpu_p95_ms=0.1286 e2e_median_ms=6.7320 e2e_p95_ms=17.4660 validation_bad=0
benchmark case=Custom-L1 MB=32 K=8 samples=20 warmup=3 cpu_median_ms=6.1940 cpu_p95_ms=8.7800 gpu_median_ms=0.1686 gpu_p95_ms=0.2043 e2e_median_ms=6.8320 e2e_p95_ms=9.4460 validation_bad=0
benchmark case=Custom-L1 MB=16 K=1 samples=20 warmup=3 cpu_median_ms=3.0820 cpu_p95_ms=4.0710 gpu_median_ms=0.0305 gpu_p95_ms=0.0355 e2e_median_ms=3.4540 e2e_p95_ms=4.5020 validation_bad=0
benchmark case=Custom-L1 MB=16 K=4 samples=20 warmup=3 cpu_median_ms=2.9720 cpu_p95_ms=3.5570 gpu_median_ms=0.0599 gpu_p95_ms=0.0661 e2e_median_ms=3.3760 e2e_p95_ms=4.1490 validation_bad=0
benchmark case=Custom-L1 MB=16 K=8 samples=20 warmup=3 cpu_median_ms=3.0900 cpu_p95_ms=3.5970 gpu_median_ms=0.0975 gpu_p95_ms=0.1044 e2e_median_ms=3.6630 e2e_p95_ms=4.3360 validation_bad=0
roundtrip samples=100 median_us=126.000 p95_us=261.000
budget tag=final segment=local hr=0x00000000 budget=32945209344 usage=22093824 reservation_available=16606822400 reservation=0
budget tag=final segment=nonlocal hr=0x00000000 budget=50222837760 usage=27918336 reservation_available=25245636608 reservation=0
completed=1 caveat=allocation_and_budget_do_not_prove_physical_BAR_size_or_residency; repeated_reads_may_hit_GPU_cache
```

### mode0_telemetry.log

```text
eGPU-DX12-Booster v0.2 enabled=1 mode=0 spoof_heap_properties=0 min_buffer_bytes=4096 max_buffer_bytes=67108864 min_heap_bytes=65536 max_heap_bytes=134217728 max_total_bytes=1073741824; descriptor_create_counts_are_not_execution_bindings; promotion_counters_are_cumulative
device_cap device=0000021c3a2c0650 options16_hr=00000000 gpu_upload_supported=1
device instrumented base + Device4/8/9/10 when supported
promotion mode=0 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=0 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=0 promote_attempts=0 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=15 root_promoted_binds=0 map_calls=1 map_upload_calls=1 map_promoted_calls=0 map_explicit_reads=0
snapshot dt_s=2.016 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=15 unique_upload_pool_bytes=33554432 cumulative_bound_pool_bytes=503316480 upload_default_copies=0 upload_default_bytes=0 default_readback_copies=0 default_readback_bytes=0 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=15 resolve_readback=15 resolve_default=0 resolve_other=0 submissions=15 commandlists=15 fence_events=15 fence_polls=0 resources_created=16 hook_failures=0
promotion mode=0 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=0 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=0 promote_attempts=0 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=69 root_promoted_binds=0 map_calls=1 map_upload_calls=1 map_promoted_calls=0 map_explicit_reads=0
snapshot dt_s=2.000 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=54 unique_upload_pool_bytes=33554432 cumulative_bound_pool_bytes=1811939328 upload_default_copies=0 upload_default_bytes=0 default_readback_copies=3 default_readback_bytes=786432 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=54 resolve_readback=54 resolve_default=0 resolve_other=0 submissions=57 commandlists=57 fence_events=57 fence_polls=0 resources_created=0 hook_failures=0
promotion mode=0 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=0 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=0 promote_attempts=0 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=69 root_promoted_binds=0 map_calls=2 map_upload_calls=2 map_promoted_calls=0 map_explicit_reads=0
snapshot dt_s=2.015 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=69 upload_default_bytes=2315255808 default_readback_copies=4 default_readback_bytes=1048576 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=92 resolve_readback=92 resolve_default=0 resolve_other=0 submissions=96 commandlists=96 fence_events=96 fence_polls=0 resources_created=3 hook_failures=0
promotion mode=0 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=0 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=0 promote_attempts=0 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=69 root_promoted_binds=0 map_calls=2 map_upload_calls=2 map_promoted_calls=0 map_explicit_reads=0
snapshot dt_s=2.032 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=0 upload_default_bytes=0 default_readback_copies=6 default_readback_bytes=1572864 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=154 resolve_readback=154 resolve_default=0 resolve_other=0 submissions=160 commandlists=160 fence_events=160 fence_polls=0 resources_created=2 hook_failures=0
crt_exit code=0
promotion mode=0 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=0 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=0 promote_attempts=0 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=69 root_promoted_binds=0 map_calls=2 map_upload_calls=2 map_promoted_calls=0 map_explicit_reads=0
snapshot dt_s=1.500 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=0 upload_default_bytes=0 default_readback_copies=5 default_readback_bytes=1310720 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=99 resolve_readback=99 resolve_default=0 resolve_other=0 submissions=204 commandlists=204 fence_events=204 fence_polls=0 resources_created=3 hook_failures=0
```

### mode1_probe.txt

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
allocation type=5 MB=4 create_hr=00000000 map_hr=00000000 create_ms=1.0040 map_ms=1.2070 write_ms=2.9010
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=20643840 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=16 create_hr=00000000 map_hr=00000000 create_ms=2.1120 map_ms=3.3850 write_ms=13.4690
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=33226752 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=24 create_hr=00000000 map_hr=00000000 create_ms=1.6270 map_ms=4.9100 write_ms=19.4740
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=41615360 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=32 create_hr=00000000 map_hr=00000000 create_ms=1.0900 map_ms=3.3020 write_ms=26.9130
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=50003968 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=64 create_hr=00000000 map_hr=00000000 create_ms=2.8750 map_ms=10.2510 write_ms=52.0250
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=83558400 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=5 MB=256 create_hr=00000000 map_hr=00000000 create_ms=8.1950 map_ms=31.6810 write_ms=188.9970
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=284884992 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=4 create_hr=00000000 map_hr=00000000 create_ms=0.7040 map_ms=0.9710 write_ms=0.7380
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=20643840 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=16 create_hr=00000000 map_hr=00000000 create_ms=1.0400 map_ms=1.9440 write_ms=3.1430
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=33226752 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=24 create_hr=00000000 map_hr=00000000 create_ms=1.1480 map_ms=2.2940 write_ms=4.4220
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=41615360 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=32 create_hr=00000000 map_hr=00000000 create_ms=1.2120 map_ms=5.4350 write_ms=6.5520
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=50003968 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=64 create_hr=00000000 map_hr=00000000 create_ms=1.3860 map_ms=6.6660 write_ms=14.7380
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=83558400 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=before_allocation segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=before_allocation segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
allocation type=4 MB=256 create_hr=00000000 map_hr=00000000 create_ms=10.6700 map_ms=30.7010 write_ms=80.4180
budget tag=allocated segment=local hr=0x00000000 budget=32945209344 usage=284884992 reservation_available=16606822400 reservation=0
budget tag=allocated segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
budget tag=released segment=local hr=0x00000000 budget=32945209344 usage=16449536 reservation_available=16606822400 reservation=0
budget tag=released segment=nonlocal hr=0x00000000 budget=50222837760 usage=7946240 reservation_available=25245636608 reservation=0
benchmark case=Direct-UPLOAD MB=32 K=1 samples=20 warmup=3 cpu_median_ms=5.9620 cpu_p95_ms=6.6360 gpu_median_ms=0.0229 gpu_p95_ms=0.0502 e2e_median_ms=6.3240 e2e_p95_ms=7.0810 validation_bad=0
benchmark case=Direct-UPLOAD MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.0260 cpu_p95_ms=7.5000 gpu_median_ms=0.0804 gpu_p95_ms=0.1036 e2e_median_ms=6.5240 e2e_p95_ms=8.6040 validation_bad=0
benchmark case=Direct-UPLOAD MB=32 K=8 samples=20 warmup=3 cpu_median_ms=5.9440 cpu_p95_ms=6.4910 gpu_median_ms=0.1534 gpu_p95_ms=0.1799 e2e_median_ms=6.4600 e2e_p95_ms=7.1990 validation_bad=0
benchmark case=Shadow-Default MB=32 K=1 samples=20 warmup=3 cpu_median_ms=5.9560 cpu_p95_ms=6.7450 gpu_median_ms=0.0366 gpu_p95_ms=0.0469 e2e_median_ms=6.3240 e2e_p95_ms=7.2160 validation_bad=0
benchmark case=Shadow-Default MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.0770 cpu_p95_ms=6.6630 gpu_median_ms=0.0916 gpu_p95_ms=0.1022 e2e_median_ms=6.3970 e2e_p95_ms=7.1140 validation_bad=0
benchmark case=Shadow-Default MB=32 K=8 samples=20 warmup=3 cpu_median_ms=6.3590 cpu_p95_ms=8.8260 gpu_median_ms=0.1652 gpu_p95_ms=0.1756 e2e_median_ms=6.8720 e2e_p95_ms=9.3500 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=1 samples=20 warmup=3 cpu_median_ms=6.1070 cpu_p95_ms=6.8760 gpu_median_ms=0.0228 gpu_p95_ms=0.0472 e2e_median_ms=6.8430 e2e_p95_ms=10.5120 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.1410 cpu_p95_ms=6.7250 gpu_median_ms=0.0856 gpu_p95_ms=0.1045 e2e_median_ms=6.8280 e2e_p95_ms=8.7970 validation_bad=0
benchmark case=GPU_UPLOAD MB=32 K=8 samples=20 warmup=3 cpu_median_ms=6.2000 cpu_p95_ms=7.2190 gpu_median_ms=0.1532 gpu_p95_ms=0.1778 e2e_median_ms=6.7070 e2e_p95_ms=7.8920 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=1 samples=20 warmup=3 cpu_median_ms=3.0660 cpu_p95_ms=3.8020 gpu_median_ms=0.0113 gpu_p95_ms=0.0243 e2e_median_ms=3.3590 e2e_p95_ms=4.5390 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=4 samples=20 warmup=3 cpu_median_ms=2.9790 cpu_p95_ms=3.6000 gpu_median_ms=0.0524 gpu_p95_ms=0.0643 e2e_median_ms=3.3890 e2e_p95_ms=4.2360 validation_bad=0
benchmark case=GPU_UPLOAD MB=16 K=8 samples=20 warmup=3 cpu_median_ms=2.9810 cpu_p95_ms=3.8090 gpu_median_ms=0.0963 gpu_p95_ms=0.1050 e2e_median_ms=3.5000 e2e_p95_ms=4.4320 validation_bad=0
benchmark case=Custom-L1 MB=32 K=1 samples=20 warmup=3 cpu_median_ms=6.1000 cpu_p95_ms=7.3590 gpu_median_ms=0.0426 gpu_p95_ms=0.1139 e2e_median_ms=6.5390 e2e_p95_ms=8.0660 validation_bad=0
benchmark case=Custom-L1 MB=32 K=4 samples=20 warmup=3 cpu_median_ms=6.3780 cpu_p95_ms=7.1470 gpu_median_ms=0.0993 gpu_p95_ms=0.1298 e2e_median_ms=6.9710 e2e_p95_ms=7.8720 validation_bad=0
benchmark case=Custom-L1 MB=32 K=8 samples=20 warmup=3 cpu_median_ms=6.1990 cpu_p95_ms=7.5390 gpu_median_ms=0.1713 gpu_p95_ms=0.1971 e2e_median_ms=6.7670 e2e_p95_ms=8.2090 validation_bad=0
benchmark case=Custom-L1 MB=16 K=1 samples=20 warmup=3 cpu_median_ms=3.0470 cpu_p95_ms=6.7370 gpu_median_ms=0.0289 gpu_p95_ms=0.0354 e2e_median_ms=3.4820 e2e_p95_ms=8.0500 validation_bad=0
benchmark case=Custom-L1 MB=16 K=4 samples=20 warmup=3 cpu_median_ms=2.9850 cpu_p95_ms=3.9460 gpu_median_ms=0.0594 gpu_p95_ms=0.0724 e2e_median_ms=3.3740 e2e_p95_ms=4.4800 validation_bad=0
benchmark case=Custom-L1 MB=16 K=8 samples=20 warmup=3 cpu_median_ms=3.0300 cpu_p95_ms=5.0970 gpu_median_ms=0.1003 gpu_p95_ms=0.1072 e2e_median_ms=3.8000 e2e_p95_ms=5.6030 validation_bad=0
roundtrip samples=100 median_us=87.000 p95_us=139.000
budget tag=final segment=local hr=0x00000000 budget=32945209344 usage=22093824 reservation_available=16606822400 reservation=0
budget tag=final segment=nonlocal hr=0x00000000 budget=50222837760 usage=27918336 reservation_available=25245636608 reservation=0
completed=1 caveat=allocation_and_budget_do_not_prove_physical_BAR_size_or_residency; repeated_reads_may_hit_GPU_cache
```

### mode1_telemetry.log

```text
eGPU-DX12-Booster v0.2 enabled=1 mode=1 spoof_heap_properties=0 min_buffer_bytes=4096 max_buffer_bytes=67108864 min_heap_bytes=65536 max_heap_bytes=134217728 max_total_bytes=1073741824; descriptor_create_counts_are_not_execution_bindings; promotion_counters_are_cumulative
device_cap device=00000132f9dcdb90 options16_hr=00000000 gpu_upload_supported=1
device instrumented base + Device4/8/9/10 when supported
promotion mode=1 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=1 promoted_live_mb=32.000000 promoted_live_bytes=33554432 promoted_peak_bytes=33554432 promote_attempts=1 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=0 root_promoted_binds=30 map_calls=1 map_upload_calls=0 map_promoted_calls=1 map_explicit_reads=0
snapshot dt_s=2.016 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=33554432 cumulative_bound_pool_bytes=1006632960 upload_default_copies=0 upload_default_bytes=0 default_readback_copies=1 default_readback_bytes=262144 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=30 resolve_readback=30 resolve_default=0 resolve_other=0 submissions=31 commandlists=31 fence_events=31 fence_polls=0 resources_created=16 hook_failures=0
promotion_release bytes=33554432 live_bytes=0
promotion_release bytes=33554432 live_bytes=0
promotion mode=1 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=2 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=33554432 promote_attempts=2 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=0 root_promoted_binds=69 map_calls=2 map_upload_calls=0 map_promoted_calls=2 map_explicit_reads=0
snapshot dt_s=2.000 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=33554432 cumulative_bound_pool_bytes=1308622848 upload_default_copies=69 upload_default_bytes=2315255808 default_readback_copies=8 default_readback_bytes=2097152 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=177 resolve_readback=177 resolve_default=0 resolve_other=0 submissions=185 commandlists=185 fence_events=185 fence_polls=0 resources_created=3 hook_failures=0
promotion mode=1 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=2 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=33554432 promote_attempts=2 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=0 root_promoted_binds=69 map_calls=2 map_upload_calls=0 map_promoted_calls=2 map_explicit_reads=0
snapshot dt_s=2.015 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=0 upload_default_bytes=0 default_readback_copies=6 default_readback_bytes=1572864 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=138 resolve_readback=138 resolve_default=0 resolve_other=0 submissions=144 commandlists=144 fence_events=144 fence_polls=0 resources_created=2 hook_failures=0
crt_exit code=0
promotion mode=1 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=2 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=33554432 promote_attempts=2 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=0 cbv_promoted_creates=0 srv_upload_creates=0 srv_promoted_creates=0 root_upload_binds=0 root_promoted_binds=69 map_calls=2 map_upload_calls=0 map_promoted_calls=2 map_explicit_reads=0
snapshot dt_s=0.938 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=0 upload_default_bytes=0 default_readback_copies=3 default_readback_bytes=786432 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=69 resolve_readback=69 resolve_default=0 resolve_other=0 submissions=172 commandlists=172 fence_events=172 fence_polls=0 resources_created=3 hook_failures=0
```

### promoter_mode0_spoof0.txt

```text
smoke mode=0 spoof=0 expected_visible_type=2 quota_must_be_8MiB
committed_type=2 GPUVA=88080384
copy_validation_bytes=4194304 bad=0
heap_type=2 heap_size=4194304
placed_type=2
copy_validation_bytes=4194304 bad=0
quota_blocked_type=2
copy_validation_bytes=4194304 bad=0
recovered_type=2
Device4 committed_type=2
Device4 placed_type=2 heap_type=2
Device8 committed_type=2
Device8 placed_type=2 heap_type=2
Device10 committed_type=2
Device10 placed_type=2 heap_type=2
shared_buffer flags=1 hr=80070057 type=0
shared_heap flags=193 hr=80070057 type=0
shared_buffer flags=32 hr=80070057 type=0
shared_heap flags=224 hr=80070057 type=0
smoke_completed=1
```

### promoter_mode0_spoof0.log

```text
eGPU-DX12-Booster v0.2 enabled=1 mode=0 spoof_heap_properties=0 min_buffer_bytes=4096 max_buffer_bytes=67108864 min_heap_bytes=65536 max_heap_bytes=134217728 max_total_bytes=8388608; descriptor_create_counts_are_not_execution_bindings; promotion_counters_are_cumulative
device_cap device=0000018787ba33a0 options16_hr=00000000 gpu_upload_supported=1
device instrumented base + Device4/8/9/10 when supported
crt_exit code=0
promotion mode=0 gpu_upload_supported=1 promoted_heaps=0 promoted_buffers=0 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=0 promote_attempts=0 promote_fallbacks=0 quota_skips=0 cbv_upload_creates=3 cbv_promoted_creates=0 srv_upload_creates=3 srv_promoted_creates=0 root_upload_binds=0 root_promoted_binds=0 map_calls=6 map_upload_calls=6 map_promoted_calls=0 map_explicit_reads=3
snapshot dt_s=0.328 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=3 upload_default_bytes=12582912 default_readback_copies=3 default_readback_bytes=12582912 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=0 resolve_readback=0 resolve_default=0 resolve_other=0 submissions=3 commandlists=3 fence_events=3 fence_polls=0 resources_created=17 hook_failures=0
```

### promoter_mode1_spoof0.txt

```text
smoke mode=1 spoof=0 expected_visible_type=5 quota_must_be_8MiB
committed_type=5 GPUVA=88080384
copy_validation_bytes=4194304 bad=0
heap_type=5 heap_size=4194304
placed_type=5
copy_validation_bytes=4194304 bad=0
quota_blocked_type=2
copy_validation_bytes=4194304 bad=0
recovered_type=5
Device4 committed_type=5
Device4 placed_type=5 heap_type=5
Device8 committed_type=5
Device8 placed_type=5 heap_type=5
Device10 committed_type=5
Device10 placed_type=5 heap_type=5
shared_buffer flags=1 hr=80070057 type=0
shared_heap flags=193 hr=80070057 type=0
shared_buffer flags=32 hr=80070057 type=0
shared_heap flags=224 hr=80070057 type=0
smoke_completed=1
```

### promoter_mode1_spoof0.log

```text
eGPU-DX12-Booster v0.2 enabled=1 mode=1 spoof_heap_properties=0 min_buffer_bytes=4096 max_buffer_bytes=67108864 min_heap_bytes=65536 max_heap_bytes=134217728 max_total_bytes=8388608; descriptor_create_counts_are_not_execution_bindings; promotion_counters_are_cumulative
device_cap device=000002a3b7a99ef0 options16_hr=00000000 gpu_upload_supported=1
device instrumented base + Device4/8/9/10 when supported
promotion_release bytes=4194304 live_bytes=4194304
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promote_fallback kind=buffer bytes=4194304 hr=80070057
promote_fallback kind=heap bytes=4194304 hr=80070057
promote_fallback kind=buffer bytes=4194304 hr=80070057
promote_fallback kind=heap bytes=4194304 hr=80070057
crt_exit code=0
promotion mode=1 gpu_upload_supported=1 promoted_heaps=4 promoted_buffers=5 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=8388608 promote_attempts=13 promote_fallbacks=4 quota_skips=1 cbv_upload_creates=1 cbv_promoted_creates=2 srv_upload_creates=1 srv_promoted_creates=2 root_upload_binds=0 root_promoted_binds=0 map_calls=6 map_upload_calls=2 map_promoted_calls=4 map_explicit_reads=3
snapshot dt_s=0.328 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=3 upload_default_bytes=12582912 default_readback_copies=3 default_readback_bytes=12582912 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=0 resolve_readback=0 resolve_default=0 resolve_other=0 submissions=3 commandlists=3 fence_events=3 fence_polls=0 resources_created=17 hook_failures=0
```

### promoter_mode1_spoof1.txt

```text
smoke mode=1 spoof=1 expected_visible_type=2 quota_must_be_8MiB
committed_type=2 GPUVA=88080384
copy_validation_bytes=4194304 bad=0
heap_type=2 heap_size=4194304
placed_type=2
copy_validation_bytes=4194304 bad=0
quota_blocked_type=2
copy_validation_bytes=4194304 bad=0
recovered_type=2
Device4 committed_type=2
Device4 placed_type=2 heap_type=2
Device8 committed_type=2
Device8 placed_type=2 heap_type=2
Device10 committed_type=2
Device10 placed_type=2 heap_type=2
shared_buffer flags=1 hr=80070057 type=0
shared_heap flags=193 hr=80070057 type=0
shared_buffer flags=32 hr=80070057 type=0
shared_heap flags=224 hr=80070057 type=0
smoke_completed=1
```

### promoter_mode1_spoof1.log

```text
eGPU-DX12-Booster v0.2 enabled=1 mode=1 spoof_heap_properties=1 min_buffer_bytes=4096 max_buffer_bytes=67108864 min_heap_bytes=65536 max_heap_bytes=134217728 max_total_bytes=8388608; descriptor_create_counts_are_not_execution_bindings; promotion_counters_are_cumulative
device_cap device=0000021d6a08e390 options16_hr=00000000 gpu_upload_supported=1
device instrumented base + Device4/8/9/10 when supported
promotion_release bytes=4194304 live_bytes=4194304
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promotion_release bytes=4194304 live_bytes=0
promote_fallback kind=buffer bytes=4194304 hr=80070057
promote_fallback kind=heap bytes=4194304 hr=80070057
promote_fallback kind=buffer bytes=4194304 hr=80070057
promote_fallback kind=heap bytes=4194304 hr=80070057
crt_exit code=0
promotion mode=1 gpu_upload_supported=1 promoted_heaps=4 promoted_buffers=5 promoted_live_mb=0.000000 promoted_live_bytes=0 promoted_peak_bytes=8388608 promote_attempts=13 promote_fallbacks=4 quota_skips=1 cbv_upload_creates=1 cbv_promoted_creates=2 srv_upload_creates=1 srv_promoted_creates=2 root_upload_binds=0 root_promoted_binds=0 map_calls=6 map_upload_calls=2 map_promoted_calls=4 map_explicit_reads=3
snapshot dt_s=0.360 presents=0 fps=0.00 frame_median_ms=0.000 frame_p99_ms=0.000 upload_bindings=0 unique_upload_pool_bytes=0 cumulative_bound_pool_bytes=0 upload_default_copies=3 upload_default_bytes=12582912 default_readback_copies=3 default_readback_bytes=12582912 texture_copies_estimated_or_unknown=0 texture_footprint_estimated_bytes=0 resolve=0 resolve_readback=0 resolve_default=0 resolve_other=0 submissions=3 commandlists=3 fence_events=3 fence_polls=0 resources_created=17 hook_failures=0
```

### fallback_test.txt

```text
fallback_test_passed=1 committed_retry=1 heap_retry=1 original_error_preserved=1 zero_quota_gate=1 unsupported_device_gate=1 promoted_live_bytes=0 hook_failures=0
```
