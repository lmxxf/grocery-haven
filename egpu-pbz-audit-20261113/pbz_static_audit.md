# 《影之刃零》OCuLink 低帧率：只读静态逆向取证

日期：2026-11-13；依据 `/tmp/pbz_yami_task.md`。**未改游戏目录、配置、Pak 或日志，未启动/注入/附加游戏进程。** 偏移均为本机 PBZ.exe **文件偏移**，除非明确写 RVA/VA。

## 结论先行

**本次没有证据把 RTX 5090 OCuLink 的 25–33ms 帧时间归因到某个已执行函数。** 已获得可操作的静态入口，但现场文件不是一次已确认的 5090 OCuLink 采样：

- GameUserSettings.ini 第 119–123 行记录 **RTX 3080 Laptop GPU / 16GB / i9-11900H / 616.92**。
- OptiScaler.log 第 130、133、137 行同样实际创建 RTX 3080 Laptop 设备；日志最后修改于 11 月 6 日。
- 目录有第三方 `dxgi.dll`、`fakenvapi.dll`、DLSS NR 替换组件；OptiScaler.log 第 17–18 行记录 **NR 启用且 RunBeforeSR=true**。它不是纯净原版渲染链样本。

三项任务状态：

| 项目 | 结果 |
|---|---|
| PBZLOGE1 日志 | **算法/派生/公钥与头结构已还原；缺匹配私钥，未解出明文**。不是简单固定 AES 密钥可直接解密的格式 |
| 加密 Pak | 已解析 v12 footer，验证 encrypted index；候选密钥解密后 SHA-1 全不匹配，**未取得有效 AES key、未提取 ini** |
| 带宽/延迟敏感路径 | 已核实上传池参数及初始化、查询/读回/队列同步/Reflex 等入口，给出有偏移的分项验证开关；**没有把静态存在写成每帧实际启用** |

最有价值的发现：上传池构造中保存的 heap type 为 **2**，与普通 `D3D12_HEAP_TYPE_UPLOAD` 一致；并未找到把这些池切成 `GPU_UPLOAD=5` 的证据。六个 `d3d12.UploadHeap.*` 是大小/策略参数，**不是 ReBAR 开关**。另一方面，普通 UPLOAD 的 GPU 远程读取、流送拷贝、查询/读回等待，同样可能对窄 PCIe 敏感；不能因未证实 GPU_UPLOAD 就排除 PCIe 瓶颈。

## 1. 靶标、方法与完整性

| 文件 | 大小 / SHA-256 |
|---|---|
| PBZ.exe | 498,913,272 bytes；`4415933ce33476f14c837abb61a1b60af8b78cd81783896501913a7aac69e423` |
| ProjectPBZ.log | 676,116 bytes；`0bb5b981164369ca5bcc738e313d1ce4676a0d0648fd9e440ebc41e17a105721` |
| ProjectPBZ-Windows.pak | 223,726,270 bytes；`610a970e15ad9fafef5b7a4a420fb465431fb624016e4827f925469b5a8532ad` |
| GameUserSettings.ini | `cff534eb18b904d3ccc7f113a0f45e69e914e587ac029bd25ab0a1e40d77a976` |

主程序 preferred image base 为 `0x140000000`。主代码 `.idata`：raw `0x400`，RVA `0x1000`，size `0xA658000`；故本报告主要代码和明文字符串区域的 **RVA = 文件偏移 + 0xC00**，VA 再加 image base。其他节不能机械套此关系。`.rsrc` raw `0xA658400`，保存大量 UTF-16/ASCII 字符串；后面还有其他代码/数据区，不能由某一字符串的缺失证明全程序不存在某功能。

方法：只读 PE/导入/异常表分析、Capstone 反汇编、RIP 相对交叉引用、CVar 注册与初值核验、Pak footer/AES-ECB/SHA-1 候选验证。脚本和依赖只置于 `/tmp/pbz_audit/`。

主要辅助材料：

- `input-hashes.txt`：源文件指纹。
- `strings.json`、`xrefs.json`：重点字符串与代码引用。
- `cvars-strings.json`：6,631 条筛选所得字符串，含帮助文字，**不是宣称 6,631 个全部已注册 CVar**。
- `cvar-candidates.tsv`：1,049 条相关名称/提示字符串子集，方便继续检索。
- `cvar-regs.json`、`key-cvar-register.txt`、`upload-ctor.txt`：注册、默认值、上传池构造。
- `crypto-start.txt`、`log-dis.txt`、`crypto-caller.txt`、`key-and-register.txt`：日志加密链。
- `pak-probe.json`：Pak 布局与候选校验结果。
- `optiscaler-evidence.txt`：有行号的第三方运行日志摘录。

## 2. 日志加密：为什么没能直接解开

### 2.1 不只是一个 magic

关键函数/指令：

| 文件偏移 | 证据 |
|---:|---|
| `0xB526EE0` | `PBZLOGE1` 8-byte magic |
| `0xB526EE8` | ASCII `pbz-log-v1`，10 bytes，是 KDF info 的域分隔文字，**不是密钥** |
| `0x4814F60` | 密钥协商/输出头初始化函数入口（VA `0x144815B60`） |
| `0x4814FB8` | 算法 ID `0x40A`，对应 OpenSSL X25519 |
| `0x4814FF0–0x4815022` | 没有提供临时私钥时创建上下文、keygen，生成新的临时密钥对 |
| `0x4815035–0x481505E` | 导出并检查 32-byte 临时公钥 |
| `0x4815073–0x4815085` | 随机生成 16-byte IV |
| `0x481508B–0x481510E` | 将传入的 32-byte 接收方公钥构造成 peer，导出 32-byte X25519 shared secret |
| `0x4815199` | ID `0x40C`，OpenSSL HKDF |
| `0x48151F8–0x48152C6` | 设置 SHA-256、空 salt、32-byte shared secret、90-byte info，并导出 32-byte 会话 key |
| `0x48152DF–0x481531B` | 写 magic、版本/算法字节、64-byte 头、临时公钥及 IV |
| `0x4815329–0x4815347` | 失败路径清 key；随后清理 shared secret 缓冲 |
| `0x4816CDB` / `0xB527B70` | 使用固定十六进制字符串构造**接收方公钥** |
| `0x4816D85–0x4816D96` | 调上述初始化时，optional 临时私钥及 IV 指针均为零，因此走随机生成 |
| `0x48170FD–0x481711C` | 建立流密码上下文，以派生 key 和 IV 初始化加密 |
| `0x4817167–0x481717C` | 建立 cipher 后清理暂存 key、关闭其有效标记 |

算法识别有额外校验：本机 libcrypto 的 NID 映射为 `1034=X25519, 1036=HKDF, 672=SHA256, 906=AES-256-CTR`。游戏内 digest descriptor 在 `0xCE28160`，首字段 672；cipher descriptor 在 `0xCE27C80 / 0xCE27CE0`，字段为 NID 906、block size 1、key length 32、IV length 16。cipher 选择入口为 VA `0x149049CB0`（文件 `0x90490B0`）。不是依据文件名猜算法。

### 2.2 本日志的头和派生式

```text
[0..7]    PBZLOGE1
[8..11]   01 01 01 00
[12..15]  40 00 00 00      header_size = 64
[16..47]  ephemeral X25519 public key (32 bytes)
[48..63]  AES-CTR IV (16 bytes)
[64..]    encrypted log stream
```

本日志临时公钥：
`e4518bfd6babdd3c4891e0aabafa05d2191eed0ecb106514cdd7c4690a113c44`

IV：`2c433f818252d8ca239762dc62044f40`

程序内接收方公钥：
`0d068454d8c1dd2b83b0f8839d7f0604e0d28316c6036ec1213e0beaf290760d`

静态还原的派生逻辑：

```text
shared = X25519(ephemeral_private, recipient_public)
info   = b"pbz-log-v1" + ephemeral_public + recipient_public + IV  # 10+32+32+16=90
key    = HKDF-SHA256(shared, salt=empty, info=info, length=32)
body   = AES-256-CTR(key, IV, plaintext)
```

同样可用 recipient_private 与头中 ephemeral_public 算 shared，但**只知道两个公钥不能算出它**。本次未取得接收方私钥或那次运行的临时私钥，亦未在静态分析中恢复当次会话 key。附近另一条 64-hex 常量不应直接叫作日志 AES 密钥：尝试作为 X25519 私钥时导出的公钥不匹配上述接收方公钥。

**交付脚本：`/tmp/pbz_audit/decrypt_pbz_log.py`。** 默认只解析并输出头，缺私钥则明确失败，不生成假明文；`--recipient-private-hex` 可提供匹配私钥继续重建派生和 CTR 解密。该解密分支尚未在真实匹配私钥上验证，脚本会先校验公钥匹配及明文前缀，避免把错误输出当日志。

**没有生成 `/tmp/ProjectPBZ_decrypted.log`，也没有从它提取到任何 D3D12/UMA/ReBAR 初始化结论。** `log-header.json`、`log-decrypt-status.txt` 记录本次失败状态。现有明文 OptiScaler.log 只作为独立来源使用，不能冒充 PBZ 主日志。

## 3. Pak AES 与配置提取

footer 取证：

```text
file offset of magic = 0x0D55C9F2
magic = 0x5A6F12E1
Pak version = 12
EncryptedIndex = 1
EncryptionKeyGuid = 00000000000000000000000000000000
IndexOffset = 0x0D4FA791
IndexSize = 84400 bytes
Index SHA-1 = a488fcef8f594aa12a7c84576e292287a9dad6fd
compression method entry includes Oodle
```

GUID 全零**不表示 key 为零**，可表示默认/未以独立 GUID 指定的密钥槽。索引加密与 Oodle 压缩也是两层，不是有 Oodle DLL 就能越过索引 AES。

尝试：扫描程序内可见 64-hex 候选，按 AES-256-ECB 解密索引，再用 footer 的 SHA-1 验真；两枚自动候选分别位于 `0xB527B70`、`0xC3B3674`，**均不匹配**。前者已经定位为日志接收方公钥，顺带排除了将它误当 Pak key 的可能。

还检查了明文 `EncryptionKey`、`FPakPlatformFile` 等引用；例如 `FPakPlatformFile` 路径相关引用出现在文件 `0x22F245A`，但未找到可验证的“默认 Pak key 填充 32-byte 常量 → AES 解密成功”链条。字符串 `FAES` / `GetPakEncryptionKey` 不出现不能证明对应代码不存在（release 可消除名称）。

**结果：未定位有效 Pak key，未解开索引，未提取 DefaultEngine.ini / DeviceProfiles / Scalability / WindowsEngine.ini。** 未创建一个装着假配置的 `/tmp/pbz_configs/`。不能把“尚未找到”升级为“已证明 key 在 Denuvo VM 内”；本次没有这样的完整定位证据。

复核脚本：`/tmp/pbz_audit/pak_probe.py`，成功条件是索引 hash 匹配，而不是解出几个像英文的字节。

## 4. 核心审计：PCIe 敏感路径

### 4.1 UploadHeap：找到了真实池初始化，没找到 ReBAR 总开关

六个参数都有代码注册，不只是字符串：

| CVar | 字符串偏移 | 注册引用 | 编译初始值 |
|---|---:|---:|---:|
| `d3d12.UploadHeap.SmallBlock.MaxAllocationSize` | `0xACAF1B0` | `0xF5D21A` | 65,536 bytes |
| `d3d12.UploadHeap.SmallBlock.PoolSize` | `0xACAF280` | `0xF5D25A` | 4,194,304 bytes |
| `d3d12.UploadHeap.BigBlock.MaxAllocationSize` | `0xACAF360` | `0xF5D11A` | 67,108,864 bytes |
| `d3d12.UploadHeap.BigBlock.PoolSize` | `0xACAF430` | `0xF5D15A` | 33,554,432 bytes |
| `d3d12.UploadHeap.PoolAllocationStrategy` | `0xACAF5D0` | `0xF5D1DA` | 1，帮助说明为 Async；0=Immediate |
| `d3d12.UploadHeap.OverFlowPoolsCount` | `0xACAF680` | `0xF5D19A` | 1 |

初值 backing storage 在 `0xDA93EBC–0xDA93ED0`。这些是**编译初值**，不是从解密日志读到的最终运行值。注册 flags 均为 `0x4`（UE `ECVF_ReadOnly`），不应承诺游戏内控制台随时可改；启动期 ini 是否被该 shipping 构建接受、是否被更高优先级覆盖，本次未实测。

构造侧实证：

- `0x306F543–0x306F56B`：读 small block pool/max 参数，名称 `Small Block Multi Buddy Allocator`（文字 `0xACB3F20`）。
- `0x306F588`：保存类型数值 **2**；`0x306F630` 保存池大小。
- `0x306F685–0x306F731`：读 big block 参数，名称 `Big Block Pool Allocator`（`0xACB3F68`）；传给下级构造的配置首值在 `0x306F70F` 写 **2**。
- `0x306F745–0x306F7C4`：构造 `Fast Constant Page Multi Buddy Allocator`，同样保存类型 **2**。

这些数据和命名支持该上传分配路径使用普通 UPLOAD heap，而非 GPU_UPLOAD=5。六个参数的帮助也只谈分配块、池和预分配，不谈 BAR、heap placement 或开关。

针对 ASCII/UTF-16 明文搜索，未检出 `norebar`、`ReBAR` 或 `GPU_UPLOAD` 入口；`Resizable` 命中主要是其他容器/脚本类型。**没有找到可推荐的 `-norebar`、`r.D3D12.UseGPUUploadHeaps` 一类本构建实证开关。** 不应把其他 UE 版本的网上配置抄进来当本游戏已支持。

边界：构造路径使用普通 UPLOAD，不证明全程序/驱动/第三方插件永不建立 CPU-visible VRAM。普通 UPLOAD 也会形成 GPU 从系统内存经 PCIe 读取的流量；仅改变池大小不会自动减少每帧上传字节数，更不会把 x4 变成 x16。

### 4.2 固定每帧工作：同步/查询是候选，不是已测 25ms 的函数

| 路径 | 本构建静态证据 | 可以说什么 / 不能说什么 |
|---|---|---|
| graphics→async-compute 等待 | `r.D3D12.SyncGraphicsCopyOpsToAsyncCompute` 字符串 `0xACBA0A0`，注册 `0xF5DA30`；帮助 `0xACB9E80` 明说 begin-frame pool relocation / RT compaction 后 signal graphics、async queue wait | 确有队列同步策略；编译默认 **0**，若运行仍为 0，反复设 0 不会产生优化 |
| 遮挡查询等待 | `r.NumBufferedOcclusionQueries` 字符串 `0xA6B98A8`、引用 `0x2D68023`；帮助明确缓冲更多帧可降低 CPU 等结果 stall | 查询/读回延迟可对 PCIe 往返敏感；没有逐帧等待时长证明 |
| HZB / feedback readback | `r.HZBOcclusion` `0xAAC1EC8`，注册 `0xF3D5CA`；`HZBGPUReadback` `0xAC1F1C0`；`r.OcclusionFeedback.Enable` `0xAC21320` | 有读回/反馈代码；关闭 HZB 不等于关闭所有遮挡查询，也可能增加绘制负担 |
| Nanite streaming readback | `r.Nanite.Streaming.Readback.UseAsyncCopy` `0xB2FF7A0`，注册 `0xFBB9CA`；帮助 `0xB2FF720` 明说 async copy engine | 是适合对照的队列路线；0/1 哪个快不能静态判断 |
| GPU skin cache | `r.SkinCache.Mode` `0xB22E368`，注册 `0xFB1BE0`，编译默认 1；`AsyncCompute` `0xB22F528` / `0xFB296A` | 这是 GPU compute skinning cache，不等于每帧把完整顶点数据从 CPU 回传；骨骼/输入上传是否主导需 trace |
| Niagara | `fx.NiagaraAllowGPUParticles` `0xB5B9A50` / `0xFF02B6`；`fx.NiagaraAllowComputeShaders` `0xB5B98D8` / `0xFF01D0`；`NiagaraFlushReadback` `0xB617E58` | 编译具备 GPU 粒子/读回路径；不能因此声称当前关卡每帧同步读回 |
| NNE ORT / DirectML | `DirectML.dll` `0xD12F0F0`；UTF-16 库名 `0xCA22880`；`DirectML Execution Provider.` `0xCA21A40`；`nne.ort.enableprofiling` `0xCA1F460` / `0x122D52D` | 证明包含运行时和 provider 能力；没有模型实例/调用频率/逐帧张量拷贝证据。profiling 不是关闭 NNE 的开关 |
| Reflex | `t.Streamline.Reflex.Enable` `0xB50D8A8` / `0xFE4E30`，编译默认 0；Mode `0xB50DCB0` / `0xFE4F50`，默认 1；HandleMaxTickRate `0xB50DDC0` / `0xFE4F0D`，默认 true | 插件可以接管限帧/低延迟 pacing；编译默认和游戏运行设置不是一回事，需实际值 |
| render/game-thread pacing | `r.OneFrameThreadLag` `0xAD3EAB0` / `0xF6C3B0`，默认1；`r.FinishCurrentFrame` `0xA6BA540`，运行查找引用 `0x30F727B` | 完成当前帧/缩短队列会增加串行程度；不能把降低延迟的设置当提高吞吐的通用优化 |

说明：NNE 字符串偏移已与附件 `strings.json` 自动核对；神经网络 DLL 的存在绝不能推出游戏每帧调用它。UE 引擎和插件常把未用于该场景的能力也编进 shipping 包。

### 4.3 现场明文日志提供的限制与线索

OptiScaler.log（**不是 PBZ 主日志**）：

- 第 1 行：加载自定义 dev 构建 `OptiScaler v10.0.0-dev (8f71f73_lmxxf_staged)`。
- 第 17–18 行：NR enabled、RunBeforeSR=true。
- 第 119 行：该次日志称 DxgiSpoofing 和 DxgiVRAM disabled，未进行对应 hook；不能据此证明所有其他 hook 均关闭。
- 第 130/133/137 行：RTX 3080 Laptop；第 134 行也枚举/尝试了 Microsoft Basic Render Driver，不能把枚举中出现软件设备就说最终使用软件渲染。
- 第 551/565/588 行：NR 插件自报约 6.55–7.03ms total；后段还见约 8ms。**这是该 3080 样本中插件自己的时域，不能搬到 5090 OCuLink，也不能与游戏帧时间简单相加。**

因此，在没有干净基线和同场景 GPU/CPU 时间线前，连“这是游戏原生 RHI 的固定成本”也尚未证明。

## 5. 只列本构建有证据的调节入口

下表是未来单项 A/B 候选，**本次未执行、未写 ini、未启动游戏**。普通 runtime CVar 可尝试放在 `Engine.ini` 的 `[SystemSettings]`；这是 UE 常见入口，不保证 PBZ shipping 接受全部项，必须核验实际值/日志，不能只凭文件写入就判定生效。不要把这些任意塞进 GameUserSettings.ini 无关 section 后期待自动生效。

| 候选设置 | 用途与限制 |
|---|---|
| `r.FinishCurrentFrame=0` | 保持帧间缓冲，排除强制每帧完成；若原已0则无变化。关闭低延迟强串行可增加输入延迟 |
| `r.OneFrameThreadLag=1` | 保留 game/render thread 重叠；不是 PCIe 专属优化，编译已默认1 |
| `t.Streamline.Reflex.Enable=0` / `t.Streamline.Reflex.Mode=0` | 对照 Reflex pacing；优先游戏 UI 关闭且先关闭依赖它的 FG；游戏可能按设置重写 CVar |
| `t.Streamline.Reflex.HandleMaxTickRate=0` | 单独检查 Reflex 接管帧率限制，不等价关闭整个 Streamline |
| `r.Nanite.Streaming.Readback.UseAsyncCopy=0` 与 `1` | 比较读回走异步 copy 的效果；不能预判哪边快 |
| `r.HZBOcclusion=0` | 对照 HZB 路径，**并非关闭全部遮挡查询**，可能反而增加 GPU 绘制 |
| `r.NumBufferedOcclusionQueries` 增加少量缓冲帧 | 若证实 query 等待再试；更多帧会增加结果陈旧，先查询现值/支持范围，不盲设巨大数 |
| `r.SkinCache.Mode=0` | 仅作诊断。帮助 `0xB22E120` 明确：禁用要求 `r.SkinCache.CompileShaders!=2`；可能有画面/功能影响，不能承诺总可关 |
| `r.SkinCache.AsyncCompute=0` 与 `1` | 隔离异步 compute 调度，不等于改变 CPU/GPU 数据拷贝总量 |
| `fx.NiagaraAllowGPUParticles=0` | 重度裁剪 GPU 粒子用于诊断，有可见特效变化，不能作为无损优化 |
| `fx.NiagaraAllowComputeShaders=0` | 同类重度诊断；可能移除效果而非自动安全回退CPU |
| `r.D3D12.SyncGraphicsCopyOpsToAsyncCompute=0/1` | 只在疑似队列同步问题时核对；静态默认0，帮助将1定义为主动增加跨队列同步，不应当万能提速开关 |

`d3d12.UploadHeap.*` 六项为启动期/ReadOnly 分配参数，优先级较低，不推荐无证据扩大到数百 MB。`nne.ort.enableprofiling` 仅用于进一步诊断，不是性能开关；**未找到可证实的全局 NNE/DirectML 禁用 CVar**。

GameUserSettings.ini 的直接字段：第 53 行 `bUseVSync=False`、65 行 `FrameRateLimit=0`，已是前台不限帧的意图；但第 42 行 **`FrameRateLimit_WhenBackgrounded=30`**、第40行 battery=60 仍在。须先确认 OCuLink 测试窗口确实前台且游戏没有错误判定后台/电源状态。30 这一值是实盘配置，不证明游戏当时真的走后台分支。

本次未验证新的专用启动参数。**不要写入 `-norebar` 冒充已找到功能。** 通用 `-ExecCmds` 等即使某 UE 构建支持，也需 PBZ shipping 运行核验；本报告不承诺用启动参数绕过 ReadOnly/游戏覆写。

## 6. 对根因假说的排序

这是下一轮排查优先级，不是静态证明的性能结论：

1. **先匹配采样对象与渲染链。** 当前给到的明文日志是3080+第三方NR，不是5090 OCuLink；先取得相同场景、相同FG/NR/插件设置的 x4/x16 对照，否则配置差异足以解释部分帧率差。
2. **先排帧率/前后台/Reflex pacing。** 分辨率无关不等于必然带宽瓶颈；硬限帧、CPU瓶颈、同步等待、驱动调度都能给相同表象。配置明确存在后台30上限。
3. **再分 PCIe“总字节吞吐”与“往返同步”。** 纹理/几何流送、常量/骨骼上传可能不随像素分辨率等比例下降；查询/读回等待则可能在字节量很小时也受延迟影响。需 CPU wait 和 GPU copy/queue 时间线区分。
4. **不要优先押 CPU 直写远端 VRAM。** 本次实际查到的 upload 池构造使用2；GPU_UPLOAD=5/显式 ReBAR 使用没有成立证据。不能为了贴合假说把普通UPLOAD改叫GPU_UPLOAD。
5. **DirectML 每帧回传暂列未证。** DLL和 provider 字符串仅证明能力存在，没有调用频率；不能直接归罪，也不能为了“关闭AI”捏造一个开关。

还需区分显示回传：若 OCuLink 显卡渲染后回传笔记本内屏，降低游戏**内部渲染**分辨率不一定降低固定输出表面的回传尺寸；外接显示器直连5090的结果才有区分力。本次没有显示拓扑/PCIe协商代际与运行链路实测，不能把“x4”进一步当成某个已知 GB/s 数字。

## 7. 未完成事项与交付边界

- 日志未解密；没有拿到 PBZ 自身的 D3D12 Adapter/VRAM/UMA/ReBAR/特性开启清单，不能造日志行号。
- Pak key 未得；没有提取任何 `.ini`。未证明密钥所在保护段，不继续盲猜。
- 没有测量5090 OCuLink的帧时间、PCIe流量、CPU栈、GPU队列或每帧NNE调用，故没有“确定根因”和“已经修复”。
- 已完成可复用的只读取证与有偏移的开关清单；若继续，最有区分力的是**相同场景 x4/x16 GPU/CPU 时间线**，而不是把上表所有开关一次全关掉。单项对照才能定位。

附：Microsoft 对 UPLOAD/GPU_UPLOAD 的区别与 UE flags 解释，供核对语义：

- [D3D12_HEAP_TYPE](https://learn.microsoft.com/en-us/windows/desktop/api/d3d12/ne-d3d12-d3d12_heap_type)
- [D3D12 GPU Upload Heaps specification](https://microsoft.github.io/DirectX-Specs/d3d/D3D12GPUUploadHeaps.html)
- [UE EConsoleVariableFlags](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Core/EConsoleVariableFlags)

本报告未借“静态分析”之名修改任何游戏文件；所有新产物位于 `/tmp`。

复核结果：PBZ.exe、加密日志、Pak、GameUserSettings.ini 四项 SHA-256 前后完全一致。
