@echo off
chcp 65001 >nul
set BASE=C:\AI\Wan22-ComfyUI
set APP=%BASE%\ComfyUI_windows_portable\ComfyUI
set PY=%BASE%\ComfyUI_windows_portable\python_embeded\python.exe
set TRITON_DEFAULT_FP_FUSION=1
set PYTHONUNBUFFERED=1
set PYTHONNOUSERSITE=1
set HF_HOME=%BASE%\cache\hf
set TORCH_HOME=%BASE%\cache\torch
set TRITON_CACHE_DIR=%BASE%\cache\triton
set TORCHINDUCTOR_CACHE_DIR=%BASE%\cache\inductor
set PIP_CACHE_DIR=%BASE%\cache\pip
set TEMP=%BASE%\cache\temp
set TMP=%BASE%\cache\temp
for /f "delims=" %%i in ('dir /b /s "%BASE%\tools\ffmpeg\ffmpeg.exe" 2^>nul') do set "FFMPEG_DIR=%%~dpi"
if defined FFMPEG_DIR set "PATH=%FFMPEG_DIR%;%PATH%"
echo ============================================================
echo   ComfyUI Foreground Console (Wan 2.2 + SageAttention 2)
echo   WebUI / API : http://192.168.31.50:8188
echo   Press Ctrl+C or close window to stop cleanly!
echo ============================================================
cd /d "%APP%"
"%PY%" -s "%APP%\main.py" --listen 0.0.0.0 --port 8188 --windows-standalone-build --disable-auto-launch --disable-xformers --reserve-vram 3 --use-sage-attention --input-directory "%BASE%\input" --output-directory "%BASE%\output" --temp-directory "%BASE%\temp" --user-directory "%BASE%\user"
