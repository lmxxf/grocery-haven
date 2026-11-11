#!/usr/bin/env python3
"""
Assemble the 3-minute AI anime drama:
《重生宗祠夜：天命归来，唯护清雪》
- 18 native audio-visual clips (MiniMax-H3 Ref2VA on RTX 5090 32GB)
- 1280x720 @ 24fps Lanczos upscale + crisp cel-line unsharp
- EBU R128 per-clip loudness leveling + smooth micro-fades at clip boundaries
- Styled ASS subtitles + Act chapter banners + Title & Finale cards
"""
import json
import os
import subprocess

BASE = "/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/minimax-h3-5090/drama_project"
MANIFEST_PATH = os.path.join(BASE, "manifest.json")
NORM_DIR = os.path.join(BASE, "clips_norm")
ASS_PATH = os.path.join(BASE, "drama_subtitles.ass")
CONCAT_LIST = os.path.join(BASE, "concat_list.txt")
RAW_MERGED = os.path.join(BASE, "merged_18_clean.mp4")
FINAL_MP4 = os.path.join(BASE, "重生宗祠夜_天命归来唯护清雪_3分钟完整版.mp4")

os.makedirs(NORM_DIR, exist_ok=True)


def fmt_ass_time(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(manifest, clip_dur=10.125):
    header = """[Script Info]
Title: 重生宗祠夜：天命归来，唯护清雪
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Dialogue,WenQuanYi Micro Hei,34,&H00FFFFFF,&H0000FFFF,&H00141010,&H78000000,1,0,0,0,100,100,1.2,0,1,3.0,1.5,2,60,60,36,1
Style: SystemVO,WenQuanYi Micro Hei,33,&H0078E8FF,&H0000FFFF,&H00221808,&H80000000,1,0,0,0,100,100,1.5,0,1,3.0,1.5,2,60,60,36,1
Style: MainTitle,WenQuanYi Micro Hei,56,&H0088E6FF,&H00FFFFFF,&H00101018,&HA0000000,1,0,0,0,100,100,4.0,0,1,4.0,2.5,8,60,60,95,1
Style: SubTitle,WenQuanYi Micro Hei,24,&H00E8E8EC,&H00FFFFFF,&H00101018,&H90000000,0,0,0,0,100,100,2.5,0,1,2.4,1.2,8,60,60,165,1
Style: ChapterTag,WenQuanYi Micro Hei,26,&H0090E2FF,&H00FFFFFF,&H0012121A,&H88000000,1,0,0,0,100,100,2.5,0,1,2.5,1.2,7,42,42,34,1
Style: FinalePoem,WenQuanYi Micro Hei,38,&H00B8ECFF,&H00FFFFFF,&H00121018,&H90000000,1,0,0,0,100,100,3.0,0,1,3.4,1.8,2,60,60,68,1
Style: FinaleCredit,WenQuanYi Micro Hei,23,&H00DFDFE6,&H00FFFFFF,&H00121018,&H90000000,0,0,0,0,100,100,2.0,0,1,2.2,1.0,8,60,60,52,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []

    # Opening main title overlay during first 3.0s of clip_01 (before dialogue starts at ~2.8s)
    events.append(
        f"Dialogue: 3,{fmt_ass_time(0.20)},{fmt_ass_time(2.75)},MainTitle,,0,0,0,,{{\\fad(350,450)}}《重生宗祠夜：天命归来，唯护清雪》"
    )
    events.append(
        f"Dialogue: 3,{fmt_ass_time(0.35)},{fmt_ass_time(2.75)},SubTitle,,0,0,0,,{{\\fad(350,450)}}RTX 5090 × MiniMax-H3 全本地直出 · AI 国漫有声短剧"
    )

    # Four Act top-left subtle chapter tags
    acts = [
        (0, "第一幕 · 浴火重生 · 系统觉醒"),
        (4, "第二幕 · 踏碎宗门 · 护妻降临"),
        (8, "第三幕 · 雷霆暴打 · 账本诛心"),
        (13, "第四幕 · 月夜花亭 · 许定终身"),
    ]
    for clip_idx, act_title in acts:
        t0 = clip_idx * clip_dur + (2.90 if clip_idx == 0 else 0.25)
        t1 = t0 + 3.40
        events.append(
            f"Dialogue: 2,{fmt_ass_time(t0)},{fmt_ass_time(t1)},ChapterTag,,0,0,0,,{{\\fad(300,400)}}▍{act_title}"
        )

    # Dialogue subtitles across all 18 clips
    for idx, item in enumerate(manifest):
        base_t = idx * clip_dur
        cid = item["id"]
        for sub_idx, (s_rel, e_rel, text) in enumerate(item["subtitles"]):
            t_start = base_t + float(s_rel)
            t_end = base_t + min(float(e_rel), clip_dur - 0.15)
            if cid == "clip_02" and sub_idx == 0:
                style = "SystemVO"
                line = f"{{\\fad(150,150)}}【系统】{text}"
            elif cid == "clip_18":
                style = "FinalePoem"
                line = f"{{\\fad(500,700)}}“山河万朵，不及你眉间一抹月光”"
                events.append(
                    f"Dialogue: 3,{fmt_ass_time(base_t + 3.8)},{fmt_ass_time(base_t + 9.8)},FinaleCredit,,0,0,0,,{{\\fad(600,700)}}全剧终 · 编导 / 分镜 / 合成：本地 AI 制片流水线 · 算力底座：本地 RTX 5090 (32GB)"
                )
            else:
                style = "Dialogue"
                line = f"{{\\fad(120,120)}}{text}"
            events.append(
                f"Dialogue: 1,{fmt_ass_time(t_start)},{fmt_ass_time(t_end)},{style},,0,0,0,,{line}"
            )

    with open(ASS_PATH, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    print(f"[1/4] Wrote ASS subtitles -> {ASS_PATH} ({len(events)} events)")


def normalize_clips(manifest):
    concat_lines = []
    for idx, item in enumerate(manifest):
        cid = item["id"]
        src = os.path.join(BASE, "clips_raw", f"{cid}.mp4")
        dst = os.path.join(NORM_DIR, f"{cid}_norm.mp4")

        # Gentle 0.12s audio fade-in/out to eliminate any inter-clip PCM click,
        # plus EBU R128 loudness normalization (keep clip_18 orchestral finale gentle so no noise pumping)
        if cid == "clip_18":
            af = "volume=2.2,afade=t=in:st=0:d=0.18,afade=t=out:st=9.35:d=0.75"
            vf = "scale=1280:720:flags=lanczos,unsharp=3:3:0.35:3:3:0.0,fps=24,fade=t=out:st=9.45:d=0.65"
        elif cid == "clip_01":
            af = "loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.20,afade=t=out:st=9.98:d=0.14"
            vf = "scale=1280:720:flags=lanczos,unsharp=3:3:0.35:3:3:0.0,fps=24,fade=t=in:st=0:d=0.35"
        else:
            af = "loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.10,afade=t=out:st=10.00:d=0.12"
            vf = "scale=1280:720:flags=lanczos,unsharp=3:3:0.35:3:3:0.0,fps=24"

        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", src,
            "-vf", vf,
            "-af", af,
            "-ar", "48000", "-ac", "2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k",
            "-t", "10.125",
            dst,
        ]
        subprocess.check_call(cmd)
        concat_lines.append(f"file '{dst}'")
        print(f"  normalized {cid} ({idx+1}/18)")

    with open(CONCAT_LIST, "w", encoding="utf-8") as f:
        f.write("\n".join(concat_lines) + "\n")
    print(f"[2/4] All 18 clips normalized into {NORM_DIR}")


def concat_and_burn():
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", CONCAT_LIST,
        "-c", "copy", RAW_MERGED,
    ])
    print(f"[3/4] Concatenated clean master -> {RAW_MERGED}")

    # Escape path for libass filter
    ass_escaped = ASS_PATH.replace("\\", "/").replace(":", "\\:")
    subprocess.check_call([
        "ffmpeg", "-y", "-v", "error",
        "-i", RAW_MERGED,
        "-vf", f"ass='{ass_escaped}'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        FINAL_MP4,
    ])
    size_mb = os.path.getsize(FINAL_MP4) / (1024 * 1024)
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", FINAL_MP4
    ], text=True))
    dur = float(probe["format"]["duration"])
    print(f"[4/4] DONE! Final 3-minute drama: {FINAL_MP4} ({dur:.2f}s, {size_mb:.2f} MB)")


def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    build_ass(manifest, clip_dur=10.125)
    normalize_clips(manifest)
    concat_and_burn()


if __name__ == "__main__":
    main()
