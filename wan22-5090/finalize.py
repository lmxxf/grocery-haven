import json,time,hashlib,sys,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));from wan22_generate import request,OPENER
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
inv=load(R/'logs/installation_inventory.json');assert inv['versions']['torch']=='2.15.0+cu132';assert inv['gpu_smoke']['capability']==[12,0]and inv['gpu_smoke']['fp8_scaled_mm_finite']and inv['gpu_smoke']['sdpa_finite'];assert inv['attention_benchmark']['state']=='pass'
assert len(inv['models'])==6 and all(f['actual_sha256']==f['sha256']and f['verified']for f in inv['models'])
cases=[]
for name in ['t2v_sdpa','t2v_sage','i2v_sage']:
 x=load(R/'logs'/f'{name}_result.json');assert x['manual_visual_review']=='pass'and x['automatic_basic_video_checks']=='pass';p=Path(x['video']);assert hashlib.sha256(p.read_bytes()).hexdigest()==x['video_sha256'];q=load(p.with_suffix('.quality.json'));assert q['decoded_frames']==81 and q['near_black_frames']==q['near_uniform_frames']==0;assert x['gpu_total_peak_MiB_sampled_500ms']<32607;x['all_frame_basic_checks']=q;cases.append(x)
api=load(R/'logs/api_smoke.json');ws=load(R/'logs/websocket_smoke.json');assert api['status']=='pass'and ws['data']['type']=='status'
xml=ET.fromstring((R/'logs/startup_task.xml').read_text(encoding='utf-8-sig'));ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'};assert xml.find('.//t:BootTrigger',ns)is not None;assert xml.find('.//t:UserId',ns).text in ['SYSTEM','S-1-5-18']
server='http://192.168.31.50:8188';stats=request(server,'/system_stats');queue=request(server,'/queue');assert not queue['queue_running']and not queue['queue_pending'];assert '--use-sage-attention'in stats['system']['argv']
with OPENER.open(server)as h:assert h.status==200
bundle={'state':'PASS','time':time.time(),'windows_root':inv['windows_root'],'web_url':server,'hardware':inv['gpu_smoke'],'software':inv['versions'],'model_inventory':inv['models'],'attention_microbenchmark':inv['attention_benchmark'],'cases':cases,'api_export_and_websocket':'pass','startup':'SYSTEM AtStartup task configured; manually started and verified; not reboot tested','final_backend':'sage','gpu_cache_released':True,'temporary_download_relay':'stopped','inference_requires_spark':False,'validation_scope':'81-frame 832x480 20-step standard T2V SDPA/Sage and I2V Sage; all-frame statistical checks plus first/middle/last keyframe visual inspection, not a guarantee for arbitrary settings'}
(R/'results.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2,allow_nan=False))
models='\n'.join('|'+f['path'].split('/')[-1]+'|'+f['path'].split('/')[1]+'|'+f'{f["size"]/1e9:.3f} GB'+'|已核验|'for f in inv['models'])
bench='\n'.join('|'+x['name']+'|'+f'{x["server_execution_seconds"]:.3f} s'+'|'+f'{x["client_wall_seconds"]:.3f} s'+'|'+f'{x["gpu_total_peak_MiB_sampled_500ms"]:,.0f} MiB / {x["gpu_total_peak_MiB_sampled_500ms"]/1024:.2f} GiB'+'|'+f'{x["bytes"]/1e6:.3f} MB'+'|'+f'{81/x["server_execution_seconds"]:.3f} fps'+'|'for x in cases)
links='\n'.join('- '+x['name']+'：[MP4]('+str(Path(x['video']).relative_to(R))+')；[首帧]('+str(Path(x['keyframe_checks'][0]['path']).relative_to(R))+')；[中帧]('+str(Path(x['keyframe_checks'][1]['path']).relative_to(R))+')；[末帧]('+str(Path(x['keyframe_checks'][2]['path']).relative_to(R))+')'for x in cases)
b=inv['attention_benchmark'];speed=cases[0]['server_execution_seconds']/cases[1]['server_execution_seconds']
readme=fr'''# RTX 5090 Windows 原生 Wan2.2 14B FP8

2026-11-11 验收 **PASS**。T2V/I2V 双专家、浏览器界面、HTTP/WS、Linux/Windows CLI 和实际 MP4 均已跑通；所有 GPU 推理在5090，笔记本只提交接口、下载与CPU解码。

## 入口与路径

- WebUI/API：**http://192.168.31.50:8188**，局域网直接访问；主机原生Win11，无WSL依赖。
- 安装根目录：`C:\AI\Wan22-ComfyUI\`。
- ComfyUI：`ComfyUI_windows_portable\ComfyUI\`，v0.44.0；便携Python：`ComfyUI_windows_portable\python_embeded\python.exe`（3.13.14）。
- **PyTorch {inv['versions']['torch']} / CUDA13.2**，驱动621.14，sm_120实际FP8矩阵运算与SDPA通过；没有改系统Python/PATH或安装全局CUDA工具链。
- Triton Windows：`{inv['versions']['triton-windows']}`；SageAttention：`{inv['versions']['sageattention']}`。Sage wheel是CUDA13.0系列、Torch2.10及以上稳定ABI包，已在本机Torch2.15/cu132上实测通过，不是凭版本名推定兼容。
- FFmpeg：**{inv['ffmpeg_version']}**，位于根目录`tools\ffmpeg\`。
- Windows输出：`C:\AI\Wan22-ComfyUI\output\`；输入：`input\`；日志：`logs\`；服务配置：`server_config.json`；HF/Torch/Triton/Inductor缓存指定到根目录`cache\`。

## 启停与浏览器

根目录双击：

- `start_comfy_api.bat`：启动当前配置后端；当前为已验证的Sage。
- `start_comfy_sdpa.bat`：稳健原生SDPA路径。
- `start_comfy_sage.bat`：Sage路径。
- `open_comfy_ui.bat`：打开本机浏览器。
- `release_gpu_keep_api.bat`：请求释放模型缓存，HTTP服务保留。
- `stop_comfy_api.bat`：停止本套服务并释放GPU；管理员操作会按Windows机制请求提升权限。

已注册 **`Wan22-ComfyUI` SYSTEM / AtStartup** 后台任务，监听`0.0.0.0:8188`，防火墙仅放行`192.168.31.0/24`。已现场启动验证，**没有为了验收重启主机**。切换后端仅在队列空闲时允许；Sage启动失败自动改回SDPA，运行中视频失败不冒称能自动识别所有黑屏问题。

交付时模型缓存已释放，整卡占用约3134MiB，服务仍运行。推理不依赖Spark：安装用临时下载中转已关闭，关闭后Sage继续生成、I2V全程完成。

工作流侧栏已放入 `Wan22_T2V_20steps_FP8.json` 与 `Wan22_I2V_20steps_FP8.json`。都是平铺核心节点，**原版20步、CFG3.5、shift5、前10步高噪/后10步低噪、81帧16fps**，无额外自定义节点或Lightning LoRA。I2V的默认`reference.png`来自实测T2V首帧，可在Load Image里自行上传替换。原始API图在`workflows/`与本机同名目录。

## CLI：Prompt / 首帧 → 轮询 → MP4自动取回

本机Linux/WSL（Python3标准库即可；有ffmpeg/ffprobe时会自动抽首/中/末帧）：

```bash
python3 /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wan22-5090/wan22_generate.py --prompt "A fox walking through a sunny meadow" --seed 20261111
```

```bash
python3 /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wan22-5090/wan22_generate.py --prompt "The same character walks forward, smooth camera tracking" --image /path/to/reference.png --seed 42
```

Spark也已放置客户端：`/home/lmxxf/work/wan22-5090/wan22_generate.py`。Windows本机可用：

```bat
C:\AI\Wan22-ComfyUI\generate.bat --prompt "A fox walking through a sunny meadow" --seed 20261111
```

支持`--server`、`--width/--height`、`--frames`（4n+1）、`--fps`、`--steps`、`--split-step`、`--cfg`、`--output-dir`、`--unload-after`。默认832×480/81帧/20步；CLI输出`job_*.json`保存seed、完整API图、任务ID、history、耗时、MP4哈希与ffprobe信息。可`--resume <prompt_id>`恢复取片；若ComfyUI重启已丢失旧RAM history，请保留本地job记录并按原参数重新提交。客户端本地超时/中断不等于取消远端排队任务。

`--workflow`适用于随附固定节点ID的API模板，仍会更新Prompt、seed、尺寸与步数；不是任意第三方图的通用参数猜测器。

HTTP入口已实测：`POST /prompt`、`GET /history/<id>`、`GET /view`、`POST /upload/image`；WebSocket `/ws?clientId=...`已完成真实握手。无需另写中间API服务。

## 权重清单

来源固定到[Comfy-Org/Wan-2.2](https://huggingface.co/Comfy-Org/Wan-2.2/tree/ee6f4a40737a995bf5818954cfce6d59443b0f04)，原`Wan_2.2_ComfyUI_Repackaged`链接现重定向到此仓库。相对ComfyUI的`models/`：

|文件|子目录|大小（十进制）|SHA256|
|---|---|---:|---|
{models}

完整官方LFS哈希及独立重算结果在[installation_inventory.json](logs/installation_inventory.json)。14B共用Wan2.1 VAE；本次I2V没有CLIP Vision节点，也无需另下CLIP Vision权重，已实际跑通。FP8指官方scaled权重；ComfyUI内部是自动混合精度，部分计算日志显示FP16，不宣称全链所有算子均以FP8运行。

## 真机账本

共同设置：832×480、81帧、16fps，H.264 MP4，无音轨，成片时长5.063秒；20步原版，不含4-step蒸馏LoRA。

|任务|服务端执行耗时|CLI总耗时|整卡显存峰值|MP4大小|生成吞吐|
|---|---:|---:|---:|---:|---:|
{bench}

显存为`nvidia-smi`每500ms采样的**整卡峰值**，包含桌面与CUDA上下文，不能当作模型独占精确峰值。服务端耗时取history执行时间戳，含模型加载/编码/解码/保存；CLI额外含轮询、下载与抽帧。16fps是播放帧率，最后一列是81/生成耗时，两者不同。

这轮T2V Sage整段为首条SDPA的约1/{speed:.2f}耗时；文件缓存、加载和并发下载状态并非严格冷启动A/B，不外推成固定提速比例。Sage为近似attention，姿态/细节可有差异。

独立attention微测：B=1/H=40/N=4096/D=128/BF16，warm CUDA events均值10次，SDPA **{b['cuda_event_ms_mean10']['sdpa']:.3f}ms**、Sage **{b['cuda_event_ms_mean10']['sage']:.3f}ms**；相对L2差 **{b['relative_l2_sage_vs_sdpa']:.2%}**，两者有限。它不是整段视频速度/画质分数。

## 视频与关键帧

{links}

三条视频均CPU解码全部81帧：无近黑屏、近纯色帧，存在连续帧变化；人工逐一看了每条首/中/末3帧，主体清晰、运动/位置连贯，背景浅景深为预期效果。统计筛查不等于对任意Prompt的画质保证。原始显存CSV、client/history和图像统计在`logs/`及各视频旁`.quality.json`。

另已用ffmpeg不重编码拼出[10秒两镜头演示](outputs/concat_demo.mp4)，只是硬切拼接示例，无配音或额外故事生成；命令与清单为`ffmpeg -f concat -safe 0 -i outputs/concat_demo.txt -c copy outputs/concat_demo.mp4`。

## 复核与维护

- [results.json](results.json)：软件、模型与三条任务的完整数值。
- [deployment_acceptance.json](deployment_acceptance.json)：最终交付哈希与PASS。
- `sources/`保存发布元数据、官方工作流、实际节点schema；`scripts/`保存Windows部署/启动/监测脚本。
- 日常生成不需运行下载脚本。重新下载/更新时，脚本里的Spark临时中转地址需先启动；本次没有改系统代理，完成后已停掉中转与一次性安装任务。
- 本次不安装可选Lightx2V/Lightning LoRA，避免把4步蒸馏当原版20步验收。
- 仅增加本套目录、计划任务和LAN防火墙规则，未修改任何游戏文件/驱动。若移除服务：停止本套任务、删除`Wan22-ComfyUI`任务与`Wan22-ComfyUI-LAN-8188`规则即可；模型/视频保留与否由目录持有人决定。

来源：[Comfy官方Wan2.2教程](https://docs.comfy.org/tutorials/video/wan/wan2_2)、[ComfyUI v0.44.0](https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.44.0)、[Sage Windows构建](https://github.com/woct0rdho/SageAttention/releases/tag/v2.2.0-windows.post6)。
'''
readme=readme.replace('\\\\','\\')
(R/'README.md').write_text(readme)
artifacts={}
for p in [R/'README.md',R/'results.json',R/'wan22_generate.py',R/'logs/installation_inventory.json',*R.glob('workflows/*.json'),*R.glob('outputs/**/*.mp4'),*R.glob('outputs/**/*.png')]:artifacts[str(p.relative_to(R))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
accept={'state':'PASS','time':time.time(),'model_hashes':6,'real_video_cases':3,'manually_inspected_keyframes':9,'api_http_websocket':True,'startup_task_configured':True,'reboot_tested':False,'final_backend':'sage','service_live':True,'gpu_cache_released':True,'inference_requires_download_proxy':False,'artifacts':artifacts}
(R/'deployment_acceptance.json').write_text(json.dumps(accept,ensure_ascii=False,indent=2));(R/'deployment_status.json').write_text(json.dumps({'state':'PASS','time':time.time(),'web_url':server,'readme':'README.md','results':'results.json','acceptance':'deployment_acceptance.json'},indent=2));print('DEPLOYMENT_PASS',[(x['name'],x['server_execution_seconds'],x['gpu_total_peak_MiB_sampled_500ms'])for x in cases])
