#!/usr/bin/env python3
"""Submit MiniMax H3 AV jobs to ComfyUI and verify the returned MP4."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parent
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
TURBO = {
    ("fl2va", 4): "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
    ("fl2va", 8): "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
    ("ref2va", 4): "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors",
}


def request(server, route, body=None, content_type="application/json"):
    if isinstance(body, dict):
        body = json.dumps(body).encode()
    req = urllib.request.Request(server + route, body, {"Content-Type": content_type})
    try:
        with HTTP.open(req, timeout=120) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode(errors="replace")) from exc


def upload(server, path):
    boundary = uuid.uuid4().hex
    name = uuid.uuid4().hex + path.suffix.lower()
    prefix = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    data = prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    result = request(server, "/upload/image", data, f"multipart/form-data; boundary={boundary}")
    return "/".join(filter(None, [result.get("subfolder"), result["name"]]))


def graph(mode, prompt, width, height, frames, steps, seed, turbo, images, prefix):
    nodes = {}

    def add(key, kind, **inputs):
        nodes[key] = {"class_type": kind, "inputs": inputs}
        return [key, 0]

    model = add("1", "UNETLoader", unet_name=f"minimax_h3_{mode}_pruned_int8_convrot.safetensors", weight_dtype="default")
    clip = add("2", "CLIPLoader", clip_name="qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", type="minimax", device="default")
    vae = add("3", "VAELoader", vae_name="minimax_h3_video_vae_int8_convrot.safetensors")
    audio_vae = add("4", "VAELoader", vae_name="minimax_h3_audio_vae_fp32.safetensors")
    if turbo:
        model = add("5", "LoraLoaderModelOnly", model=model, lora_name=TURBO[mode, turbo], strength_model=1.0)
    cond_inputs = dict(clip=clip, vae=vae, prompt=prompt, width=width, height=height, length=frames)
    for index, name in enumerate(images):
        if name is None:
            continue
        image = add(str(20 + index), "LoadImage", image=name)
        slot = f"ref_images.ref_image_{index}" if mode == "ref2va" else ("first_frame", "last_frame")[index]
        cond_inputs[slot] = image
    if mode == "ref2va":
        cond_inputs.update(audio_vae=audio_vae, ref_image_size="match")
    conditioning = add("6", "MiniMaxH3ReferenceToVideo" if mode == "ref2va" else "MiniMaxH3ImageToVideo", **cond_inputs)
    noise = add("7", "RandomNoise", noise_seed=seed)
    sampler = add("8", "KSamplerSelect", sampler_name="res_multistep")
    sigmas = add("9", "BasicScheduler", model=model, scheduler="simple", steps=steps, denoise=1.0)
    guider = add("10", "BasicGuider", model=model, conditioning=conditioning)
    latent = add("11", "SamplerCustomAdvanced", noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=["6", 1])
    video = add("12", "VAEDecode", samples=latent, vae=vae)
    audio = add("13", "VAEDecodeAudio", samples=latent, vae=audio_vae)
    movie = add("14", "CreateVideo", images=video, audio=audio, fps=24.0)
    add("15", "SaveVideo", video=movie, filename_prefix=prefix, format="mp4")
    return nodes


def inspect(path):
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ]))
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in info["streams"] if stream["codec_type"] == "audio")
    if (audio["sample_rate"], audio["channels"]) != ("32000", 2):
        raise RuntimeError(f"Expected 32 kHz stereo, got {audio['sample_rate']} Hz / {audio['channels']} channels")
    pcm = array.array("f", subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-f", "f32le", "-"
    ]))
    rms = math.sqrt(sum(value * value for value in pcm) / len(pcm)) if pcm else 0
    if not math.isfinite(rms) or rms <= 0:
        raise RuntimeError("Silent or invalid audio")
    frames = int(video["nb_frames"])
    frame_dir = path.with_suffix("")
    frame_dir.mkdir(exist_ok=True)
    selection = "+".join(f"eq(n\\,{n})" for n in sorted({0, frames // 2, frames - 1}))
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", "select=" + selection,
        "-vsync", "0", str(frame_dir / "frame_%02d.png")
    ], check=True)
    return {"ffprobe": info, "audio_rms": rms, "keyframes": [str(p) for p in sorted(frame_dir.glob("frame_*.png"))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="http://192.168.31.50:8188")
    parser.add_argument("--mode", choices=["fl2va", "ref2va"], default="fl2va")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--frames-images", nargs="+", type=Path, help="FL2VA first and optional last frame")
    parser.add_argument("--ref-images", nargs="+", type=Path)
    parser.add_argument("--first-frame", type=Path)
    parser.add_argument("--last-frame", type=Path)
    parser.add_argument("--duration", type=float, default=6)
    parser.add_argument("--width", type=int, default=832)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--turbo", type=int, choices=[4, 8])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--timeout", type=float, default=14400)
    parser.add_argument("--resume", help="Retrieve a previously submitted prompt ID")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    server = args.server.rstrip("/")
    steps = args.steps if args.steps is not None else args.turbo or 20
    anchors = args.first_frame or args.last_frame
    if anchors and (args.mode != "fl2va" or args.frames_images or args.ref_images):
        parser.error("Use --first-frame/--last-frame separately from list inputs in FL2VA mode")
    images = [args.first_frame, args.last_frame] if anchors else args.ref_images or args.frames_images or []
    if any(side < 32 or side > 16384 or side % 2 for side in (args.width, args.height)):
        parser.error("Width and height must be even and between 32 and 16384")
    render_width = ((args.width + 31) // 32) * 32
    render_height = ((args.height + 31) // 32) * 32
    crop = (render_width, render_height) != (args.width, args.height)
    if crop and not args.resume:
        print(f"Rendering {render_width}x{render_height}, then center-cropping the MP4 to {args.width}x{args.height}", file=sys.stderr)
    if not math.isfinite(args.duration) or not 0 < args.duration <= 150 or not 1 <= steps <= 10000:
        parser.error("Invalid duration or step count")
    if args.turbo and ((args.mode, args.turbo) not in TURBO or steps != args.turbo):
        parser.error("Turbo requires its matching LoRA and step count. Ref2VA supports 4-step Turbo.")
    if args.mode == "ref2va" and not args.resume and (args.frames_images or not 1 <= len(images) <= 9):
        parser.error("Ref2VA requires 1–9 --ref-images")
    if args.mode == "fl2va" and (args.ref_images or len(images) > 2):
        parser.error("FL2VA accepts up to two --frames-images")
    if not args.resume and not args.prompt_file:
        parser.error("--prompt-file is required for submission")
    if any(path is not None and not path.is_file() for path in images):
        parser.error("Image file missing")
    frames = max(5, round(args.duration * 24))
    frames += (5 - frames % 17) % 17
    if frames > 3600:
        parser.error("Aligned frame count exceeds node maximum")
    seed = args.seed if args.seed is not None else secrets.randbits(32)
    if not 0 <= seed < 2**64:
        parser.error("Seed outside uint64 range")
    tag = uuid.uuid4().hex[:12]
    if not args.resume:
        prompt = args.prompt_file.read_text(encoding="utf-8-sig").strip()
        if not prompt:
            parser.error("Prompt file is empty")
        if args.dry_run:
            print(json.dumps(graph(args.mode, prompt, render_width, render_height, frames, steps, seed, args.turbo, [p.name if p else None for p in images], "H3/" + tag), ensure_ascii=False, indent=2))
            return
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("ffmpeg and ffprobe are required for AV verification")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    record = args.output_dir / f"job_{tag}.json"
    started = time.time()
    state = {
        "state": "preparing", "started": started,
        "source_images": [str(p) if p else None for p in images],
        "parameters": {
            "mode": args.mode, "seed": seed, "steps": steps, "turbo": args.turbo,
            "requested_duration": args.duration, "effective_frames": frames,
            "effective_duration": frames / 24, "requested_size": [args.width, args.height],
            "render_size": [render_width, render_height], "fps": 24,
            "sampler": "res_multistep", "scheduler": "simple",
            "guidance": "BasicGuider (single conditioning, effective CFG=1)",
        },
    }
    try:
        if args.resume:
            prompt_id = args.resume
        else:
            names = [upload(server, p) if p else None for p in images]
            workflow = graph(args.mode, prompt, render_width, render_height, frames, steps, seed, args.turbo, names, "H3/" + tag)
            state["workflow"] = workflow
            state["server"] = request(server, "/system_stats")
            prompt_id = request(server, "/prompt", {"prompt": workflow, "client_id": tag})["prompt_id"]
        state.update(state="queued", prompt_id=prompt_id)
        record.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print(f"prompt_id={prompt_id} frames={frames} record={record}", flush=True)
        last_progress = -1
        while time.time() - started < args.timeout:
            item = request(server, "/history/" + urllib.parse.quote(prompt_id, safe="")).get(prompt_id)
            if item:
                state["history"] = item
                status = item.get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(str(status))
                if status.get("completed"):
                    break
            elapsed = int(time.time() - started)
            if elapsed // 15 != last_progress:
                print(f"waiting {elapsed}s", flush=True)
                last_progress = elapsed // 15
            time.sleep(3)
        else:
            raise TimeoutError(f"Resume with --resume {prompt_id}")
        file = next(f for node in item["outputs"].values() for results in node.values() if isinstance(results, list) for f in results if isinstance(f, dict) and f.get("filename", "").endswith(".mp4"))
        query = urllib.parse.urlencode({key: file.get(key, "") for key in ("filename", "subfolder", "type")})
        path = args.output_dir / (tag + "_" + Path(file["filename"]).name)
        partial = path.with_suffix(".part")
        with HTTP.open(server + "/view?" + query, timeout=300) as source, partial.open("wb") as target:
            shutil.copyfileobj(source, target)
        partial.replace(path)
        if crop and not args.resume:
            state["server_file_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            cropped = path.with_suffix(".crop.mp4")
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(path),
                "-vf", f"crop={args.width}:{args.height}", "-c:v", "libx264",
                "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", str(cropped)
            ], check=True)
            cropped.replace(path)
        state.update(video=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        state.update(inspect(path))
        video = next(stream for stream in state["ffprobe"]["streams"] if stream["codec_type"] == "video")
        if not args.resume and (video["width"], video["height"], int(video["nb_frames"])) != (args.width, args.height, frames):
            raise RuntimeError(f"Unexpected video dimensions or frame count: {video}")
        if video["r_frame_rate"] != "24/1":
            raise RuntimeError(f"Unexpected frame rate: {video['r_frame_rate']}")
        timestamps = {event: payload.get("timestamp") for event, payload in status.get("messages", [])}
        if timestamps.get("execution_start") and timestamps.get("execution_success"):
            state["server_seconds"] = (timestamps["execution_success"] - timestamps["execution_start"]) / 1000
        state.update(state="complete", wall_seconds=time.time() - started)
        print(path, flush=True)
    except BaseException as exc:
        state.update(state="failed", error=str(exc))
        raise
    finally:
        record.write_text(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
