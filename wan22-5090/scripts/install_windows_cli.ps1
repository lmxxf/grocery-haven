$base='C:\AI\Wan22-ComfyUI'
$ffmpeg=(Get-ChildItem "$base\tools\ffmpeg" -Filter ffmpeg.exe -Recurse | Select-Object -First 1).DirectoryName
$bat="@echo off`r`nsetlocal`r`nset `"PATH=$ffmpeg;%PATH%`"`r`n`"%~dp0ComfyUI_windows_portable\python_embeded\python.exe`" -s `"%~dp0scripts\wan22_generate.py`" --output-dir `"%~dp0client_outputs`" %*`r`n"
[IO.File]::WriteAllText("$base\generate.bat",$bat,[Text.Encoding]::ASCII)
& cmd.exe /c "$base\generate.bat --resume cfd14cb0-30d1-47f8-90c2-aaada068ed58 --no-keyframes"
