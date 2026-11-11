#!/usr/bin/env python3
"""
Rewrite all 18 prompts with clean close-mic Mandarin voice syntax (zero gasp/wind/hiss/raspy adjectives),
backup old clips_raw -> clips_raw_v1_noisy, re-render all 18 clips in 4-step Turbo on 5090,
and re-run assemble_drama.py + upgrade_audio_ost.py (without destructive afftdn) to produce a crystal-clear 3-minute drama!
"""
import glob
import os
import re
import shutil
import subprocess
import sys

BASE = "/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/minimax-h3-5090/drama_project"
PROMPTS_DIR = os.path.join(BASE, "prompts")

# Copy our verified crystal-clear clip_01 prompt and its already-rendered MP4!
shutil.copyfile("/tmp/clip_01_minimal_sound.txt", os.path.join(PROMPTS_DIR, "clip_01.txt"))

# Clean voice delivery replacements & soundscape replacements for clips 02..18
CLEAN_SOUNDSCAPES = {
    "clip_02": ("Quiet night courtyard and two clean close-mic foreground Mandarin voices.", "Quiet, sparse guqin notes under the voices."),
    "clip_03": ("Quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse low cello notes under the voice."),
    "clip_04": ("Quiet indoor hall, a single clean wooden tap at 00:07.500, and a clean close-mic foreground Mandarin female voice.", "Quiet, sparse bamboo flute notes under the voice."),
    "clip_05": ("A clean wooden door opening sound at 00:00.500, then quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse cello notes under the voice."),
    "clip_06": ("Quiet indoor hall and two clean close-mic foreground Mandarin voices.", "Quiet, sparse guzheng notes under the voices."),
    "clip_07": ("Quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse low string notes under the voice."),
    "clip_08": ("Quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse cello notes under the voice."),
    "clip_09": ("A single clean crisp slap impact at 00:02.000, then quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse low string notes under the voice."),
    "clip_10": ("Two clean martial arts impact thuds at 00:02.000, then quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse guqin notes under the voice."),
    "clip_11": ("Soft paper pages settling at 00:01.000, then quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse cello notes under the voice."),
    "clip_12": ("Quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse low string notes under the voice."),
    "clip_13": ("Quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse guqin notes under the voice."),
    "clip_14": ("Quiet indoor hall and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse piano notes under the voice."),
    "clip_15": ("Quiet moonlit pavilion and a clean close-mic foreground Mandarin female voice.", "Quiet, sparse guzheng notes under the voice."),
    "clip_16": ("Quiet moonlit pavilion and a clean close-mic foreground Mandarin male voice.", "Quiet, sparse cello notes under the voice."),
    "clip_17": ("Quiet moonlit pavilion and two clean close-mic foreground Mandarin voices.", "Quiet, sparse guzheng notes under the voices."),
    "clip_18": ("Quiet moonlit garden.", "Soft, gentle guzheng and flute chord."),
}

NOISY_VOICE_PATTERNS = [
    (r"says loudly in a sharp, condescending young male voice:", "says clearly in a clean foreground Mandarin male voice,"),
    (r"says in a clear, crystalline, slightly trembling yet resolute young female voice:", "says clearly in a clean foreground Mandarin female voice,"),
    (r"declares in a commanding, thunderous young male voice that echoes through the hall:", "says clearly and firmly in a clean foreground Mandarin male voice,"),
    (r"speaks in a soft, breathless, astonished young female voice:", "says clearly in a gentle, clean foreground Mandarin female voice,"),
    (r"says in a warm, gentle, reassuring young male voice:", "says clearly in a warm, clean foreground Mandarin male voice,"),
    (r"sneers loudly in a shrill, haughty young male voice:", "says clearly in a sharp, clean foreground Mandarin male voice,"),
    (r"speaks in an icy, overpowering young male voice:", "says clearly and firmly in a clean foreground Mandarin male voice,"),
    (r"shrieks in a panicked, pained young male voice:", "says clearly in a startled, clean foreground Mandarin male voice,"),
    (r"says in an effortless, commanding young male voice:", "says clearly and calmly in a clean foreground Mandarin male voice,"),
    (r"announces in a clear, resounding young male voice:", "says clearly and firmly in a clean foreground Mandarin male voice,"),
    (r"pleads in a broken, trembling, cowardly young male voice:", "says clearly in a pleading, clean foreground Mandarin male voice,"),
    (r"proclaims in a calm, authoritative, resonant young male voice:", "says clearly and calmly in a clean foreground Mandarin male voice,"),
    (r"says softly in a warm, affectionate young male voice:", "says clearly in a warm, clean foreground Mandarin male voice,"),
    (r"asks in a gentle, emotional young female voice:", "asks clearly in a gentle, clean foreground Mandarin female voice,"),
    (r"speaks in a deep, sincere, deeply moving young male voice:", "says clearly in a warm, clean foreground Mandarin male voice,"),
    (r"asks earnestly in a tender, solemn young male voice:", "asks clearly in a warm, clean foreground Mandarin male voice,"),
    (r"replies in a sweet, clear, heartfelt young female voice:", "replies clearly in a sweet, clean foreground Mandarin female voice,"),
    (r"an ethereal, crystal-clear female system voice \(S1\) says in an off-screen voiceover:", "a clean, calm female voice (S1) says clearly in voiceover,"),
    (r"says in a firm, resonant young male voice:", "says clearly and firmly in a clean foreground Mandarin male voice,"),
]

NOISY_VISUAL_WORDS = [
    ("in a storm of wind, ", ""),
    ("with a shockwave of dust and swirling autumn leaves", "smoothly"),
    ("billowing in the gale", "draping neatly"),
    ("Golden aura sparks crackle subtly around his shoulders", "Warm golden light rims his shoulders"),
    ("Wind and golden sparks surge intensely around the frame", "Soft golden light glows calmly around the frame"),
    ("a dazzling golden shockwave erupts from beneath his boots, sending fine spiderweb cracks glowing with gold light across the stone", "soft golden light glows beneath his boots across the stone"),
]

for cid, (s_scape, n_music) in CLEAN_SOUNDSCAPES.items():
    p = os.path.join(PROMPTS_DIR, f"{cid}.txt")
    txt = open(p, encoding="utf-8").read()
    for pat, rep in NOISY_VOICE_PATTERNS:
        txt = re.sub(pat, rep, txt)
    for old_w, new_w in NOISY_VISUAL_WORDS:
        txt = txt.replace(old_w, new_w)
    # Replace overall_soundscape and non_diegetic_music sections cleanly
    head = txt.split("overall_soundscape:")[0].rstrip()
    txt_new = f"{head}\n\noverall_soundscape:\n{s_scape}\n\nnon_diegetic_music:\n{n_music}\n"
    open(p, "w", encoding="utf-8").write(txt_new)

print("[Clean Rebuild 1/4] Rewrote all 18 prompts with clean studio-voice syntax!", flush=True)

# Backup noisy clips_raw -> clips_raw_v1_noisy
raw_dir = os.path.join(BASE, "clips_raw")
bak_dir = os.path.join(BASE, "clips_raw_v1_noisy")
if not os.path.exists(bak_dir) and os.path.exists(raw_dir):
    shutil.move(raw_dir, bak_dir)
os.makedirs(raw_dir, exist_ok=True)

# Reuse the already verified clean clip_01 we just rendered!
verified_01 = "/home/lmxxf/work/memory-of-my-gemini/doc/grocery-haven/minimax-h3-5090/drama_project/clips_20step/clip_01_test/8326b93e88c8_8326b93e88c8_00001_.mp4"
if os.path.exists(verified_01):
    shutil.copy2(verified_01, os.path.join(raw_dir, "clip_01.mp4"))
    print("  Copied verified clean clip_01.mp4!", flush=True)

prog_file = os.path.join(BASE, "render_progress.json")
if os.path.exists(prog_file):
    os.remove(prog_file)

print("[Clean Rebuild 2/4] Rendering remaining 17 clean clips on RTX 5090...", flush=True)
subprocess.check_call([sys.executable, os.path.join(BASE, "render_all_18.py")])

print("[Clean Rebuild 3/4] Normalizing and assembling 720p clean master...", flush=True)
subprocess.check_call([sys.executable, os.path.join(BASE, "assemble_drama.py")])

print("[Clean Rebuild 4/4] Mixing 3-Act OST + clean voice + burning ASS subtitles...", flush=True)
subprocess.check_call([sys.executable, os.path.join(BASE, "upgrade_audio_ost.py")])
print("ALL CLEAN REBUILD COMPLETE!", flush=True)
