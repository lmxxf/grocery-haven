#!/usr/bin/env python3
"""
1. Download ACE-Step 1.5 Turbo AIO (10.03 GB) to 5090 ComfyUI models/checkpoints via ModelScope aria2c.
2. Generate 3 custom Chinese Donghua OST tracks on RTX 5090 ComfyUI:
   - ost_act1_suspense.flac (42s: Dark Tense Guqin, Cello & Night Suspense)
   - ost_act2_battle.flac   (92s: Epic Chinese Martial Arts Battle Drums, Erhu & Pipa)
   - ost_act3_romance.flac  (55s: Romantic Moonlit Guzheng, Bamboo Flute & Lush Strings Finale)
3. Synthesize continuous stereo room-tone / night wind / hall ambience beds + spatialize dry dialogue + sidechain-duck OST under speech + re-render final 3-minute 720p MP4!
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import numpy as np

sys.path.insert(0, "/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/wan22-5090")
import remote_ps

SERVER = "http://192.168.31.50:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/minimax-h3-5090/drama_project"
OST_DIR = os.path.join(BASE, "ost")
os.makedirs(OST_DIR, exist_ok=True)


def api_json(route, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        SERVER + route,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def ensure_acestep_downloaded():
    print("[Step 1] Checking / Downloading ace_step_1.5_turbo_aio.safetensors on 5090...", flush=True)
    ps = r"""
$base='C:\AI\Wan22-ComfyUI'
$dir="$base\ComfyUI_windows_portable\ComfyUI\models\checkpoints"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$final="$dir\ace_step_1.5_turbo_aio.safetensors"
$expected=10025478736
if ((Test-Path $final) -and (Get-Item $final).Length -eq $expected) {
    Write-Output "ALREADY_READY"
    exit 0
}
$aria=(Get-ChildItem "$base\tools\aria2" -Filter aria2c.exe -Recurse | Select-Object -First 1).FullName
$url='https://modelscope.cn/models/Comfy-Org/ace_step_1.5_ComfyUI_files/resolve/master/checkpoints/ace_step_1.5_turbo_aio.safetensors'
$args=@('--no-proxy=*','--continue=true','--auto-file-renaming=false','--max-connection-per-server=16','--split=16','--min-split-size=16M','--file-allocation=none','--max-tries=15','--retry-wait=3','--console-log-level=warn',"--dir=$dir",'--out=ace_step_1.5_turbo_aio.safetensors.part',$url)
& $aria @args
if ($LASTEXITCODE -ne 0) { throw "aria2 failed with $LASTEXITCODE" }
$len=(Get-Item "$final.part").Length
if ($len -ne $expected) { throw "Size mismatch: $len vs $expected" }
Move-Item "$final.part" $final -Force
Write-Output "DOWNLOAD_COMPLETE"
"""
    t0 = time.time()
    proc = remote_ps.run(ps, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Download failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}")
    print(f"  5090 checkpoint ready in {time.time()-t0:.1f}s: {proc.stdout.strip().splitlines()[-1]}", flush=True)


def generate_ost_track(name: str, tags: str, structure_lyrics: str, bpm: int, keyscale: str, seconds: float, seed: int) -> str:
    out_path = os.path.join(OST_DIR, f"{name}.flac")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 100_000:
        print(f"  OST {name} already exists ({os.path.getsize(out_path)/1e6:.2f} MB), reusing.", flush=True)
        return out_path

    prompt = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "ace_step_1.5_turbo_aio.safetensors"},
        },
        "2": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["1", 0], "shift": 3.0},
        },
        "3": {
            "class_type": "TextEncodeAceStepAudio1.5",
            "inputs": {
                "clip": ["1", 1],
                "tags": tags,
                "lyrics": structure_lyrics,
                "seed": seed,
                "bpm": bpm,
                "duration": float(seconds),
                "timesignature": "4",
                "language": "zh",
                "keyscale": keyscale,
                "generate_audio_codes": True,
                "cfg_scale": 2.0,
                "temperature": 0.85,
                "top_p": 0.9,
                "top_k": 0,
                "min_p": 0.0,
            },
        },
        "4": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["3", 0]},
        },
        "5": {
            "class_type": "EmptyAceStep1.5LatentAudio",
            "inputs": {"seconds": float(seconds), "batch_size": 1},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "seed": seed,
                "steps": 8,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "denoise": 1.0,
            },
        },
        "7": {
            "class_type": "VAEDecodeAudio",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
        },
        "8": {
            "class_type": "SaveAudioAdvanced",
            "inputs": {
                "audio": ["7", 0],
                "filename_prefix": f"drama_ost/{name}",
                "format": "flac",
            },
        },
    }

    t0 = time.time()
    resp = api_json("/prompt", {"prompt": prompt})
    pid = resp["prompt_id"]
    print(f"  Submitted OST '{name}' ({seconds}s, {bpm} BPM, {keyscale}) prompt_id={pid} ...", flush=True)

    while True:
        time.sleep(1.5)
        hist = api_json(f"/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error on {name}: {json.dumps(status, ensure_ascii=False)}")
            outputs = entry.get("outputs", {})
            if "8" in outputs and "audio" in outputs["8"]:
                ainfo = outputs["8"]["audio"][0]
                qs = urllib.parse.urlencode({
                    "filename": ainfo["filename"],
                    "subfolder": ainfo.get("subfolder", ""),
                    "type": ainfo.get("type", "output"),
                })
                with OPENER.open(f"{SERVER}/view?{qs}", timeout=60) as r:
                    raw = r.read()
                with open(out_path, "wb") as f:
                    f.write(raw)
                print(f"  -> OST '{name}' rendered in {time.time()-t0:.1f}s ({len(raw)/1e6:.2f} MB) -> {out_path}", flush=True)
                return out_path


def make_ambience_bed(total_sec: float, out_wav: str):
    """
    Generate a subtle, warm stereo natural ambience bed (48kHz stereo):
    - 0..40s (Act 1 Courtyard & Hall): cold night breeze + low hall room air
    - 40..131.6s (Act 2 & 3 Grand Ancestral Hall): warm grand wooden hall acoustic room tone + subtle sub-air
    - 131.6..182.3s (Act 4 Moonlit Lotus Pavilion): gentle evening breeze over water & leaves
    Eliminates the -45 dBFS 'dead vacuum' between dialogue lines!
    """
    sr = 48000
    n = int(total_sec * sr)
    rng = np.random.default_rng(20261111)

    # Generate smooth pink/brown-ish filtered stereo noise via frequency-domain shaping
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    freqs[0] = 1.0

    def shaped_noise(slope, lp_hz, hp_hz, seed_offset):
        r = np.random.default_rng(20261111 + seed_offset)
        phases = r.uniform(0, 2 * np.pi, len(freqs))
        amps = (1.0 / (freqs ** slope))
        amps *= 1.0 / (1.0 + (freqs / lp_hz) ** 4)
        amps *= 1.0 / (1.0 + (hp_hz / freqs) ** 2)
        amps[0] = 0.0
        sig = np.fft.irfft(amps * np.exp(1j * phases), n=n).astype(np.float32)
        sig /= (np.std(sig) + 1e-9)
        return sig

    t = np.linspace(0, total_sec, n, endpoint=False, dtype=np.float32)

    # Slow organic wind modulation (0.11 Hz and 0.23 Hz gentle swells)
    wind_mod_L = 0.65 + 0.35 * np.sin(2 * np.pi * 0.11 * t) * np.cos(2 * np.pi * 0.04 * t + 0.7)
    wind_mod_R = 0.65 + 0.35 * np.sin(2 * np.pi * 0.105 * t + 1.1) * np.cos(2 * np.pi * 0.037 * t)

    wind_L = shaped_noise(0.75, 950.0, 90.0, 1) * wind_mod_L
    wind_R = shaped_noise(0.75, 950.0, 90.0, 2) * wind_mod_R

    hall_L = shaped_noise(0.95, 420.0, 55.0, 3)
    hall_R = shaped_noise(0.95, 420.0, 55.0, 4)

    leaves_L = shaped_noise(0.45, 3200.0, 600.0, 5) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.17 * t + 0.3))
    leaves_R = shaped_noise(0.45, 3200.0, 600.0, 6) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.16 * t + 1.9))

    # Envelope weights across Acts
    w_night_open = np.clip(1.0 - (t - 18.0) / 6.0, 0.0, 1.0)
    w_hall = np.clip((t - 16.0) / 5.0, 0.0, 1.0) * np.clip(1.0 - (t - 138.0) / 6.0, 0.0, 1.0)
    w_pavilion = np.clip((t - 136.0) / 6.0, 0.0, 1.0)

    L = (
        w_night_open * (0.012 * wind_L + 0.006 * hall_L)
        + w_hall * (0.009 * hall_L + 0.004 * wind_L)
        + w_pavilion * (0.010 * wind_L + 0.005 * leaves_L)
    )
    R = (
        w_night_open * (0.012 * wind_R + 0.006 * hall_R)
        + w_hall * (0.009 * hall_R + 0.004 * wind_R)
        + w_pavilion * (0.010 * wind_R + 0.005 * leaves_R)
    )

    # Smooth fade-in and fade-out
    fade_in = np.clip(t / 1.0, 0.0, 1.0)
    fade_out = np.clip((total_sec - t) / 1.5, 0.0, 1.0)
    stereo = np.stack([L * fade_in * fade_out, R * fade_in * fade_out], axis=1)
    pcm16 = np.clip(stereo * 32767.0, -32768, 32767).astype(np.int16)

    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "s16le", "-ar", str(sr), "-ac", "2", "-i", "-",
            out_wav,
        ],
        input=pcm16.tobytes(),
        check=True,
    )
    print(f"[Step 3] Built continuous room-tone & night ambience bed -> {out_wav}", flush=True)


def mix_full_soundtrack_and_video(ost1: str, ost2: str, ost3: str):
    total_dur = 18 * 10.125  # 182.25s
    amb_wav = os.path.join(OST_DIR, "ambience_bed.wav")
    make_ambience_bed(total_dur, amb_wav)

    # Build continuous 182.25s stereo BGM score from the 3 Act tracks with smooth 3.5s crossfades:
    # - ost1 (Act 1 dark guqin/cello suspense): 0.0s -> 42.5s (fades into ost2 around clip_05 door smash at 40.5s!)
    # - ost2 (Act 2 & 3 heroic martial battle): 39.0s -> 143.5s (covers clip_05..clip_14, crossfades at 140s into moonlit pavilion!)
    # - ost3 (Act 4 romantic guzheng/flute/strings): 140.0s -> 182.25s (climaxes during clip_17 & clip_18!)
    ost_full = os.path.join(OST_DIR, "ost_full_score.wav")
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error",
        "-i", ost1,
        "-i", ost2,
        "-i", ost3,
        "-filter_complex",
        (
            "[0:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:43.0,asetpts=PTS-STARTPTS,"
            "loudnorm=I=-18:TP=-2:LRA=10,afade=t=in:st=0:d=0.8[a0];"
            "[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:104.5,asetpts=PTS-STARTPTS,"
            "loudnorm=I=-17:TP=-2:LRA=10[a1];"
            "[2:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:46.5,asetpts=PTS-STARTPTS,"
            "loudnorm=I=-17:TP=-2:LRA=10,afade=t=out:st=44.0:d=2.2[a2];"
            "[a0][a1]acrossfade=d=3.5:c1=tri:c2=tri[m01];"
            "[m01][a2]acrossfade=d=4.0:c1=tri:c2=tri,atrim=0:182.25,asetpts=PTS-STARTPTS[out]"
        ),
        "-map", "[out]",
        ost_full,
    ])
    print(f"[Step 4] Assembled 3-Act continuous orchestral Chinese OST -> {ost_full}", flush=True)

    # Now mix:
    # 1. Clean dialogue/SFX stem from merged_18_clean.mp4 + subtle early-reflection room reverb so voices sit IN the hall/pavilion rather than a dry booth!
    # 2. Continuous 3-Act OST score with sidechaincompress keyed by the voice/SFX stem (ducks ~5-6 dB smoothly when characters speak, swells up in pauses and action/finale!)
    # 3. Continuous stereo ambience bed (night wind / hall air / lotus breeze) so noise floor never hits -45 dBFS vacuum!
    raw_merged = os.path.join(BASE, "merged_18_clean.mp4")
    ass_path = os.path.join(BASE, "drama_subtitles.ass")
    final_mp4 = os.path.join(BASE, "重生宗祠夜_天命归来唯护清雪_3分钟完整版.mp4")
    final_clean_mp4 = os.path.join(BASE, "merged_18_rich_audio_clean.mp4")

    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error",
        "-i", raw_merged,
        "-i", ost_full,
        "-filter_complex",
        (
            # 1) Light, transparent highpass + gentle de-esser only (voice is now natively clean from H3!):
            "[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            "highpass=f=65,deesser=i=0.18,"
            "asplit=3[vdry][vrev_in][vkey];"
            # 2) Subtle early-reflection hall space (no synthetic hiss!)
            "[vrev_in]highpass=f=160,lowpass=f=4500,aecho=0.8:0.7:28|54:0.12|0.07,volume=0.22[vwet];"
            "[vdry][vwet]amix=inputs=2:weights='1.0 0.24':normalize=0[voice_spaced];"
            # 3) Clean 3-Act OST score with sidechain ducking (acts as natural warm musical bed without white noise!)
            "[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.45[bgm_pre];"
            "[bgm_pre][vkey]sidechaincompress=threshold=0.035:ratio=3.8:attack=35:release=480:makeup=1.15[bgm_ducked];"
            # 4) Sum clean voice + ducked OST only (removed synthetic noise bed so speech has zero added hiss!)
            "[voice_spaced][bgm_ducked]amix=inputs=2:weights='1.0 0.92':normalize=0,"
            "alimiter=limit=0.93:attack=5:release=50[aout]"
        ),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "256k",
        final_clean_mp4,
    ])
    print(f"[Step 5] Mixed full cinema audio master -> {final_clean_mp4}", flush=True)

    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error",
        "-i", final_clean_mp4,
        "-vf", f"ass='{ass_escaped}'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        final_mp4,
    ])
    sz = os.path.getsize(final_mp4) / (1024 * 1024)
    print(f"[Step 6] ALL DONE! Upgraded 3-minute drama written to: {final_mp4} ({sz:.2f} MB)", flush=True)


def main():
    ensure_acestep_downloaded()
    # Refresh ComfyUI checkpoint list check
    ckpts = api_json("/object_info/CheckpointLoaderSimple")["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    print("  ComfyUI visible checkpoints:", ckpts, flush=True)
    if "ace_step_1.5_turbo_aio.safetensors" not in ckpts:
        raise RuntimeError("ace_step_1.5_turbo_aio.safetensors not visible in CheckpointLoaderSimple!")

    print("[Step 2] Generating 3 custom Chinese Donghua OST tracks on RTX 5090...", flush=True)
    ost1 = generate_ost_track(
        name="ost_act1_suspense",
        tags="Instrumental, Pure Instrumental, No Vocals, Chinese Anime Soundtrack, Dark Suspenseful Guqin, Deep Cello Tremolo, Tense Atmospheric Night Strings, Mysterious Cinematic Donghua Score, Minor Key",
        structure_lyrics="[Instrumental]\n[Intro - Deep Cello Drone & Cold Guqin Plucks]\n[Build - Rising Tense Strings & Subtle Taiko Pulse]",
        bpm=78,
        keyscale="D minor",
        seconds=46.0,
        seed=20261101,
    )
    ost2 = generate_ost_track(
        name="ost_act2_battle_symphonic",
        tags="Pure Instrumental Film Score, Epic Cinematic Dark Orchestra, Hans Zimmer & Sawano Hiroyuki Style Anime Battle Theme, Deep Thunderous Taiko War Drums, Powerful Brass Horns, Dramatic Staccato String Ostinato, Soaring Emotional Cello & Erhu Lead, Grand Revenge Climax, Minor Key",
        structure_lyrics="[Instrumental]\n[Intro - Heavy Orchestral Brass Hit & Deep Taiko Drums]\n[Main Theme - Driving Dramatic Strings Ostinato & Heroic Horns]\n[Climax - Full Symphony Orchestra & Thunderous Percussion]",
        bpm=128,
        keyscale="D minor",
        seconds=108.0,
        seed=20261188,
    )
    ost3 = generate_ost_track(
        name="ost_act3_romance",
        tags="Instrumental, Pure Instrumental, No Vocals, Romantic Chinese Fantasy Anime Finale Soundtrack, Tender Guzheng Arpeggios, Emotional Dizi Bamboo Flute, Warm Lush Symphony Strings, Moonlit Peach Blossom Love Theme",
        structure_lyrics="[Instrumental]\n[Intro - Gentle Moonlit Guzheng & Harp]\n[Theme - Emotional Bamboo Flute & Warm Strings]\n[Grand Finale - Sweeping Romantic Orchestra Swell & Lingering Chord]",
        bpm=72,
        keyscale="F major",
        seconds=50.0,
        seed=20261103,
    )

    mix_full_soundtrack_and_video(ost1, ost2, ost3)


if __name__ == "__main__":
    main()
