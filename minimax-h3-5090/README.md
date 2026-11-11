# MiniMax-H3 RTX 5090 Windows 部署

2026-11-11 验收 **PASS**。服务当前在线，地址为 **http://192.168.31.50:8188**。沿用 ComfyUI 0.44.0、PyTorch 2.15.0+cu132 与驱动621.14。安装根目录为 C:\AI\Wan22-ComfyUI。

## 立即调用

本机WSL客户端使用Python3、ffmpeg、ffprobe，GPU运算在5090。

    python3 /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/minimax-h3-5090/h3_generate.py --mode fl2va --turbo 8 --duration 6 --prompt-file /path/to/shot.txt

    python3 /home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/minimax-h3-5090/h3_generate.py --mode ref2va --turbo 4 --duration 6 --ref-images /path/to/actor.png /path/to/scene.png --prompt-file /path/to/shot.txt

原版使用 --steps 20。Turbo使用 --turbo 4 或 --turbo 8，步数须与LoRA匹配。Ref2VA提供4-step Turbo。采样沿用官方模板的BasicGuider单路条件、res_multistep、simple调度，等效CFG=1。

FL2VA可用 --first-frame、--last-frame，也可用 --frames-images first.png last.png。单尾帧使用 --last-frame。Ref2VA的 --ref-images 接受1–9张图，按命令顺序对应Picture 1到Picture 9。脚本保留prompt文件原文，标签和台词由调用方编写。

帧数从 max(5, round(duration*24)) 向上对齐到17n+5。6秒请求为158帧/6.583秒，5秒为124帧/5.167秒。渲染尺寸向上对齐32，随后居中裁切到请求尺寸。例如1280×720渲染1280×736，再裁到1280×720，音轨复制。本次实际测速固定832×480。

支持 --width、--height、--seed、--output-dir、--server、--timeout、--resume prompt_id。任务JSON保存参数、完整API图、history、耗时、MP4和关键帧。完成后自动校验视频流、32kHz双声道音轨、PCM RMS>0、帧数与尺寸。客户端超时后可以按已提交任务ID恢复取片。

## WebUI和服务

工作流侧栏已安装 **MiniMax_H3_T2VA.json** 与 **MiniMax_H3_Ref2VA.json**，均为平铺核心节点。默认分别是8-step和4-step，包含视频/音频VAE解码及CreateVideo.audio连线。20步可旁路LoRA节点，再把BasicScheduler设为20。

输入目录为 C:\AI\Wan22-ComfyUI\input。GUI人物图来自本次H3输出，庭院图来自imagegen。可替换为正式角色卡。专用前台入口为根目录 run_h3_foreground.bat，使用SDPA。已有服务在线时请直接使用接口或浏览器。

当前为手动启动的SYSTEM任务，启动触发器为零。按本次要求保持在线。剧集完成后可用现有 stop_comfy.bat 停止进程。原Wan入口和Sage包保留。

生产配置为SDPA。Sage配置下也完成一次H3 Ref2VA 4-step。该次重启后包含加载，测速条件有差异。set_backend.py在队列空闲时切换配置，并保持手动任务形式。

## 真机账本

成片均为H.264视频和32kHz双声道AAC，24fps。158帧为6.583秒，双首尾帧补测124帧为5.167秒。显存为整卡目标500ms采样，逐行刷新，实际时间戳在CSV里。

|任务|服务端执行耗时|显存采样峰值|帧数|PCM RMS|CPU转录|
|---|---:|---:|---:|---:|---|
|fl2va_8|82.491 s|31,581 MiB|158|0.1278|这一世,属于我的东西,我会亲手拿回来。|
|fl2va_4_anchors|34.829 s|31,673 MiB|124|0.1140|我回来了|
|ref2va_4|45.197 s|31,670 MiB|158|0.1339|你願意幫我嗎?我願意|
|ref2va_20|116.443 s|31,657 MiB|158|0.0964|你願意幫我嗎?我願意|
|ref2va_4_sage|67.770 s|31,657 MiB|158|0.1366|你願意幫我嗎?我願意|

Ref2VA 4-step本轮比20-step快约2.58倍。两档中文对白正确，抽帧脸型、发饰与服装接近，主观差异较小。批量分镜可先用4-step，关键镜头再选20步。

4-step音量更高，少量AAC解码采样超过全幅，比例约0.003%；20-step该比例为0，RMS更低。完整左右声道RMS、峰值和声道差异在results.json。转录、波形和音量用于本次音频核验。

场景约束较弱。人物图中包含原庭院，成片背景仍偏向该庭院，第二张独立场景图没有完整迁移。两档均有此现象。口型仅在发言时段抽帧检查，可见口部动作，逐音素对齐未量化。

第一次显存采样因nvidia-smi输出缓冲造成短片CSV不完整，正式测速已重跑。最终表格使用逐行刷新的完整记录。服务端时间包含编码、加载、采样、解码与保存，缓存状态随任务顺序变化。

- fl2va_8 [MP4](outputs/fl2va_8/996c15059e02_996c15059e02_00001_.mp4) [首帧](outputs/fl2va_8/996c15059e02_996c15059e02_00001_/frame_01.png) [中帧](outputs/fl2va_8/996c15059e02_996c15059e02_00001_/frame_02.png) [末帧](outputs/fl2va_8/996c15059e02_996c15059e02_00001_/frame_03.png)
- fl2va_4_anchors [MP4](outputs/fl2va_4_anchors/5a253e04fce9_5a253e04fce9_00001_.mp4) [首帧](outputs/fl2va_4_anchors/5a253e04fce9_5a253e04fce9_00001_/frame_01.png) [中帧](outputs/fl2va_4_anchors/5a253e04fce9_5a253e04fce9_00001_/frame_02.png) [末帧](outputs/fl2va_4_anchors/5a253e04fce9_5a253e04fce9_00001_/frame_03.png)
- ref2va_4 [MP4](outputs/ref2va_4/94f27af1ef3f_94f27af1ef3f_00001_.mp4) [首帧](outputs/ref2va_4/94f27af1ef3f_94f27af1ef3f_00001_/frame_01.png) [中帧](outputs/ref2va_4/94f27af1ef3f_94f27af1ef3f_00001_/frame_02.png) [末帧](outputs/ref2va_4/94f27af1ef3f_94f27af1ef3f_00001_/frame_03.png)
- ref2va_20 [MP4](outputs/ref2va_20/46bf87d57c44_46bf87d57c44_00001_.mp4) [首帧](outputs/ref2va_20/46bf87d57c44_46bf87d57c44_00001_/frame_01.png) [中帧](outputs/ref2va_20/46bf87d57c44_46bf87d57c44_00001_/frame_02.png) [末帧](outputs/ref2va_20/46bf87d57c44_46bf87d57c44_00001_/frame_03.png)
- ref2va_4_sage [MP4](outputs/ref2va_4_sage/eb706b5215a7_eb706b5215a7_00001_.mp4) [首帧](outputs/ref2va_4_sage/eb706b5215a7_eb706b5215a7_00001_/frame_01.png) [中帧](outputs/ref2va_4_sage/eb706b5215a7_eb706b5215a7_00001_/frame_02.png) [末帧](outputs/ref2va_4_sage/eb706b5215a7_eb706b5215a7_00001_/frame_03.png)

## 权重和来源

HF固定revision为54472221d27c695fca9621b0c3ed52f06c4af707。Windows最终采用ModelScope续传，八个文件的大小和SHA256均与HF清单匹配。Spark保留SSH跳板用途，临时下载中转已关闭。

|相对ComfyUI/models路径|大小|
|---|---:|
|vae/minimax_h3_audio_vae_fp32.safetensors|0.56 GiB|
|loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors|1.82 GiB|
|loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors|1.82 GiB|
|loras/minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors|1.82 GiB|
|vae/minimax_h3_video_vae_int8_convrot.safetensors|2.62 GiB|
|text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors|14.61 GiB|
|diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors|19.53 GiB|
|diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors|19.53 GiB|

完整哈希见h3_manifest.json与logs/download_verified.json。真实视频均使用INT8_convrot主干、NVFP4-AWQ编码器。INT8视频VAE也已独立完成编码/解码测试。

nodes_minimax_h3.py来自5090实际安装。多图接口是V3 Autogrow字段 ref_images.ref_image_0 到 ref_images.ref_image_8，每槽一图。AddGuide用于给指定帧增加图像/音频引导。CLI多参考模式直接使用ReferenceToVideo参考槽。

服务保持在线，AtStartup保持关闭。结果和哈希在results.json与deployment_acceptance.json。

来源 [Comfy官方重打包仓](https://huggingface.co/Comfy-Org/MiniMax-H3)、[MiniMax原仓](https://huggingface.co/MiniMaxAI/MiniMax-H3)、[官方模板](https://github.com/Comfy-Org/workflow_templates/tree/main/templates)。提示词指南、官方模板及本次prompt文件均保存在本目录。
