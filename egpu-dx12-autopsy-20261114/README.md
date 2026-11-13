# eGPU-DX12-Booster v0.3.1

D3D12 telemetry and optional UPLOAD → GPU_UPLOAD promotion, plus a headless hardware probe. No game binary patches.

Build with MinGW-w64:

```sh
./build.sh
./scripts/build_smoke_tests.sh
python3 scripts/check_artifacts.py
```

`./build.sh --dll-only` preserves the existing probe EXE byte-for-byte. Outputs are x64 Windows binaries, with static GCC/C++ runtime libraries and only Windows system DLL imports. The probe uses the OS `D3DCOMPILER_47.dll` for embedded HLSL; `--adapter "RTX 5090"` selects an adapter substring.

Results: [Phase 3 real PBZ game A/B](docs/phase3_game_results.md), [Phase 1 hardware probe](docs/probe_rtx5090_results.md), [Phase 2 real-host comparison and smoke tests](docs/phase2_smoke_results.md). Phases 1/2 were confined to the temporary probe directory. Phase 3 tested the real PBZ game after backing up its old patches and settings, then removed the test proxy and restored the original INI. Old patches remain in the verified backup, not the game directory.

## Configuration

Reads `egpu_booster.ini` next to the proxy. Missing INI defaults to enabled telemetry, mode=0. Unsupported mode values become mode=0. Configuration is read once at process initialization; restart the process after editing it.

```ini
[booster]
enabled=1
mode=0
min_buffer_kb=4
max_buffer_mb=64
min_heap_kb=64
max_heap_mb=128
max_total_mb=1024
spoof_heap_properties=0
```

Sizes use KiB/MiB. Bounds are inclusive. Setting `max_total_mb=0` disables promotion through the quota gate. `enabled=0` forwards without installing telemetry hooks. `mode=1` is opt-in.

## Promotion and fallback

- Checks OPTIONS16 GPUUploadHeapSupported per device. Only UPLOAD Buffer committed allocations, or UPLOAD heaps not denying buffers, within the configured sizes and atomic total quota are candidates.
- Covers base, Device4/8/9/10 inherited and versioned APIs: CommittedResource/1/2/3, Heap/1, PlacedResource/1/2. Clones properties and changes only Type to 5, leaving the caller's descriptors unchanged.
- A failed promoted creation retries the original arguments immediately, releases the reservation and increments `promote_fallbacks`. If the original allocation also fails, its HRESULT is returned unchanged. This fallback is at **creation time**; it cannot migrate an already mapped buffer back to system RAM later.
- Charges committed buffers by Width and explicit heaps by SizeInBytes, including in-flight creation reservations. Placed resources inherit their heap's promotion status without a second charge. Final Release reclaims the owning charge. `promoted_buffers` counts committed owning allocations, `promoted_heaps` counts owning heaps; placed buffers are not counted twice.
- The quota is requested bytes, not exact WDDM residency or rounded physical committed memory. No shadow-copy fallback or automatic live migration is implemented.
- `spoof_heap_properties=1` reports Type=2 for promoted Resource.GetHeapProperties and Heap.GetDesc. Actual tracking remains Type=5. Correct slots are Resource 14 and Heap 8 (Heap.GetDesc uses COM's aggregate-return ABI); Resource.Map is slot 8. Native GPU_UPLOAD allocations are not spoofed.

## Telemetry

Logs `egpu_booster.log` every 120 successful non-test Presents or roughly two seconds, including headless programs. Application ExitProcess/CRT exit imports are intercepted for a best-effort final flush **outside DllMain**. Forced termination, unhooked exits, or fatal failures can still lose the last interval. The proxy is pinned for process lifetime and does not support hot unloading.

- All 20 DXGI exports and ordinals match the target's system DLL. Assembly forwarding preserves integer/XMM registers and stack parameters. Initialization is lazy, outside DllMain; system DXGI is loaded by absolute path.
- Application import-table and GetProcAddress interception finds D3D12CreateDevice. Rescans every two seconds; Windows/driver modules are excluded. No instruction detours or third-party runtime.
- Tracks resource/heap lifetime and a sorted GPUVA interval table. Observes root CBV/SRV, VBV/IBV, buffer/texture copies, query resolves by destination heap, queue submissions, fence events/polls, and factory-created SwapChain Present/Present1.
- Device CreateConstantBufferView/CreateShaderResourceView counters classify UPLOAD and automatically promoted buffers. These are **descriptor creation evidence**, not descriptor-table execution counts. Descriptor copies/table bindings, indirect/work-graph reads and GPU-generated addresses remain untraced.
- Resource.Map counts UPLOAD/promoted calls and nonempty explicit pReadRange declarations; a null read range is not counted as an *explicit* read declaration. Persistent mappings may be created once and used for many frames. A read declaration is reported; it cannot retroactively undo promotion.
- `promotion` records are cumulative except `promoted_live_bytes/mb` (current outstanding charge); peak and allocation/descriptor/Map totals are cumulative. `root_upload_binds` and `root_promoted_binds` are cumulative. `gpu_upload_supported` means a supported device was observed during this process, even after it is released.
- `snapshot` workload counters are interval totals. `unique_upload_pool_bytes` deduplicates resources within the interval and includes automatically promoted pools; `cumulative_bound_pool_bytes` adds the entire containing buffer on every binding. Neither is actual PCIe traffic or the shader's read length. Latest registered resource wins for aliased GPUVA ranges.
- Buffer copy bytes are exact requested lengths (including promoted-upload sources). Texture-copy byte estimates are separate, can include pitch padding and overestimate compressed formats; partial/unknown copies can report zero size.
- Workload counters are collected at **recording time**, not replayed on queue submission. Reused/discarded command lists and concurrent queues can differ from actual per-frame GPU work. Fence counters do not measure CPU wait duration. Multiple SwapChains aggregate Present intervals.
- Uses atomics/SRW locks; the binding hot path does no allocation and uses a logarithmic interval lookup. Game runtime overhead is unmeasured. Already-created devices/resources, cached early function pointers, delay-import-only early creation and alternative device factories may escape interception.

## Validation scope

The unchanged Phase 1 probe ran with the actual local DXGI proxy in mode=0 and mode=1 on RTX 5090. Supplemental tests validate descriptors, Map read declarations, committed and placed resources, versioned APIs, size/quota gating and recovery, spoofing, and driver-error retries. An isolated helper fault test covers failed promotion followed by successful original allocation for Buffer and Heap. See the report for hashes, complete logs and exact counts.

Microbenchmark success does not establish any game's speedup or UE5/Denuvo compatibility. Use this proxy alone during a subsequent application test; preserve existing OptiScaler/other dxgi.dll files. The supplied INI and the remote temporary directory are left in mode=0.

## v0.2.1 real-game changes

Adds cumulative owner allocation counts/live-byte ledgers by heap Type 1..5 and CUSTOM L1 (not physical residency), plus batched frame samples for pooled median/P99 calculation. Explicit heaps own their placed resources' bytes, so placement does not double-count. Buffer bytes are Width, texture bytes are GetResourceAllocationInfo estimates.

Real PBZ testing exposed a factory-forwarding recursion in the earlier whole-process GetProcAddress interception: v0.2.1 caches system factory entrypoints before hooks, leaves explicit system-DXGI factory lookups untouched, uses an atomic original GetProcAddress pointer, and defers startup work until a factory exists. Import scans validate RVAs against PE image bounds. It also hooks supported inherited interfaces through Device16/GraphicsCommandList12/CommandQueue1, including TryCreate CBV/SRV and CommittedResource4/PlacedResource3. Multi-factory static/dynamic smoke tests cover the previously missing simple case; the actual game tests cover the layered game runtime.

`python3 scripts/phase3_summarize.py` recomputes the Phase 3 summary and checks the three configurations, sample counts, link state, hook failures and promotion quota. Per-game results do not establish a universal optimization: in the tested PBZ save point, the 20MiB case differed by less than 1%, while the wide case was slower in this single run. See the report for precise limits and restoration paths.

## Phase 4 diagnostic profiler

[Phase 4 autopsy](docs/phase4_bottleneck_autopsy.md) records the Wukong benchmark and PBZ 4K-output DLSS Performance static/valley camera-motion data, with complete cleanup. Adds QPC original-API timing, per-thread totals, tracked fence-event waits (including null-event synchronous waits), copy Buffer/Texture classification and readback-size bins. Timings overlap across threads and are not an additive frame budget.

INI `profile_cpu=1` enables CPU timing (default); `track_bindings=0` and `track_descriptors=0` disable the per-binding/per-descriptor observation paths for lean diagnostic runs. They default to 1 for compatibility with earlier telemetry. Persistent mapped CPU reads/writes and memcpy are not measured by Map timing. v0.3.1 derives known texture-copy logical payloads via cached footprints, including nonempty source boxes; unknown formats remain explicit. No claim of resolving the original low-GPU-utilization symptom is made by this data.
