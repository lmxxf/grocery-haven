# eGPU-DX12-Booster · Phase 4 任务书（给闇 `wC:p1`：在「4K DLSS 性能档 + 大场景动态」复现 GPU ~50% 低帧率现场并做微秒级耗时拆解）

## Zero 刚刚给出的决定性现场校准（砍掉假假设！）
Zero 明确指出：
> **“不是 720p 这么低，就是 4K DLSS 性能档就很低，GPU 占用也就 50%，反正就是没啥影响。当然，场景大一些就更慢了。”**

结合你 Phase 3 测出的数据，物理图景瞬间清晰了：
- Phase 3 测的是 **4K 原生分辨率 + 小木屋前人物静止站桩**，此时 GPU SM 占用 `80.2%`，帧率 `66 FPS`（`15.07 ms`）；即便完全静止，每帧已有 **77 次 `ExecuteCommandLists`、33.6 次 `Fence::SetEventOnCompletion`、`303 MB/s` TX 读回与 `1,563 MB/s` RX 流量**。
- 当切到 **4K DLSS 性能档（内部 1080p）** 并进入 **大场景 / 移动跑图** 时，像素着色负载大降（所以 **GPU 占用掉到 ~50% 在干等！**），而与分辨率无关、随大场景几何/实例/流送膨胀的瓶颈把帧率死死按在 **30–40 FPS（25–33 ms）**！
- 更关键的是：Zero 确认这一现象在 **直插 PCIe x16 设备上不存在**，且呈现 `直插 x16 正常 -> OCuLink x4 (PBZ/黑神话卡 30-40 帧) -> USB4 (连生化危机 9 都卡)` 的严格总线梯度！

**我们绝不再盲猜具体是哪个堆，而是直接用微秒级探针在「4K DLSS 性能档 + 大场景运动（GPU ~50% 占用）」现场把那 25–33 ms 的每一毫秒拆解出来！**

---

## 本阶段执行步骤

### Step 1：给 `dxgi.dll` 增加轻量微秒级耗时去向拆解器（v0.3 Diagnostic Profiler）
在 `mode=0` 遥测中（用 `QueryPerformanceCounter` 原子累加每快照窗口的总微秒数，开销极小）：
1. **CPU 阻塞耗时拆解（每帧平均 ms）**：
   - `cpu_present_ms`：花在原始 `IDXGISwapChain::Present*` 内部的阻塞毫秒数；
   - `cpu_exec_ms`：花在原始 `ID3D12CommandQueue::ExecuteCommandLists` 内部的毫秒数（检测 WDDM 跨桥提交开销！）；
   - `cpu_map_upload_ms` / `cpu_map_readback_ms`：花在 `ID3D12Resource::Map`（按 UPLOAD vs READBACK 分类）内部的毫秒数；
   - **极其关键——Fence 等待阻塞耗时 `cpu_fence_wait_ms`**：
     游戏调 `ID3D12Fence::SetEventOnCompletion(val, hEvent)` 后，真正阻塞线程是在随后的 `WaitForSingleObject` / `WaitForSingleObjectEx` / `WaitForMultipleObjects*` 上！请记录最近传入 `SetEventOnCompletion` 的 `HANDLE` 集合（比如环形缓冲记最近 64 个 event handle），通过 IAT Hook 应用模块的 `WaitForSingleObject` / `WaitForSingleObjectEx` / `WaitForMultipleObjects` / `WaitForMultipleObjectsEx`，当等待目标包含 Fence Event 时，累加真实等待阻塞耗时 `cpu_fence_wait_ms` 与超过 `0.5 ms` 的长阻塞次数 `long_fence_waits`！（这能一锤定音看出是不是 CPU 渲染线程在等跨 OCuLink 的 Readback / 遮挡查询 / 帧同步 Fence！）
2. **拷贝明细分类拆解（区分 Buffer vs Texture 流送！）**：
   - 在 `CopyBufferRegion` / `CopyResource` / `CopyTextureRegion` 中，分别统计：
     - `upload_to_default_buffer_bytes` vs `upload_to_default_texture_bytes`（看大场景移动时是不是 Virtual Texture / Nanite 流送把 PCIe 吸爆了！）；
     - `default_to_readback_buffer_bytes` vs `default_to_readback_texture_bytes`（以及单次 Readback 的常见尺寸分布，比如 <=4KB 查询/反馈 vs >64KB HZB/流送读回）。

### Step 2：在 `rtx5090` 真机上复现「4K DLSS 性能档 + 大场景动态 + ~50% GPU 占用」现场！
我们手头有两个绝佳靶标（任选最快复现出 30–50 FPS + GPU 占用 <=60% 的一个，或两个都测）：
1. **靶标 A：《黑神话：悟空》（`D:\SteamLibrary\steamapps\common\BlackMythWukong`，AppID `2358720`，100% 纯净原版）**：
   - 主菜单自带 **「性能测试（Benchmark）」**，全程自动沿着大场景森林溪流高速运镜 2 分钟，无需人工操作跑图，且天然包含大场景 Nanite 流送、动态水面/植被与高 DrawCall！设置 **4K + DLSS 性能档（Performance，50% 超采样） + 关垂直同步 + 关帧生成（FG Off，测真实原生帧率！）** 跑一趟，抓 `egpu_booster.log` + `nvidia-smi dmon -s uct -d 1`！
2. **靶标 B：《影之刃零》（`PBZ`）**：
   - 在游戏设置中开启 **4K + DLSS 性能档（Performance） + 关 VSync + 关帧生成**，进入存档后通过 `desktop_agent` 发送移动/转视角输入走出小木屋进入开阔大场景（或触发跑动/战斗），观察是否出现 **GPU SM 占用掉到 ~50%、FPS 落在 30–50 帧** 的现象，并采集 60 秒 `v0.3` 拆解日志 + `dmon`！

### Step 3：精准归因与验证（如果当场抓到元凶，顺手验证针对性开关！）
- 拿到复现现场的 `v0.3` 拆解账本后，看清到底是：
  - **情况 1**：`rxpci` 飙到 `4,000–6,000 MB/s` 顶死 PCIe Gen4 x4 天花板（带宽饱和型，看是 Buffer 还是 Texture Copy 还是未拷 UPLOAD 直读）；
  - **情况 2**：`rxpci` 只有 `1,000–2,000 MB/s`，`sm%` ~50%，而 `cpu_fence_wait_ms` 或 `cpu_exec_ms` 每帧高达 `10–20 ms`（跨桥同步/Readback 往返延迟或高频提交阻塞型！若是 UE5 引擎，当场可测 `Engine.ini` 里的 `r.NumBufferedOcclusionQueries=4`、`r.HZBOcclusion=0`、`r.FinishCurrentFrame=0`、`r.OneFrameThreadLag=1` 或拦截合并是否有立竿见影的奇效！）。
- 测试完毕依然清理干净现场、恢复原配置，把复现数据与真凶拆解写入 `/home/lmxxf/work/egpu-dx12-booster/docs/phase4_bottleneck_autopsy.md` 汇报！
