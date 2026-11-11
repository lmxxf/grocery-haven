$base='C:\AI\Wan22-ComfyUI'
$body="@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File %~dp0scripts\start_service.ps1 -Backend sdpa`r`nif errorlevel 1 pause`r`n"
[IO.File]::WriteAllText("$base\start_comfy_api.bat",$body.Replace(' -Backend sdpa',''),[Text.Encoding]::ASCII)
[IO.File]::WriteAllText("$base\start_comfy_sdpa.bat",$body,[Text.Encoding]::ASCII)
[IO.File]::WriteAllText("$base\start_comfy_sage.bat",$body.Replace('-Backend sdpa','-Backend sage'),[Text.Encoding]::ASCII)
[IO.File]::WriteAllText("$base\open_comfy_ui.bat","@echo off`r`nstart `"`" http://127.0.0.1:8188`r`n",[Text.Encoding]::ASCII)
$stop="@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File %~dp0scripts\stop_service.ps1`r`n"
[IO.File]::WriteAllText("$base\stop_comfy_api.bat",$stop,[Text.Encoding]::ASCII)
New-Item -ItemType Directory -Force -Path "$base\user\default\workflows" | Out-Null
Copy-Item "$base\scripts\Wan22_T2V_20steps_FP8.json","$base\scripts\Wan22_I2V_20steps_FP8.json" "$base\user\default\workflows" -Force
'LAUNCHERS_AND_WORKFLOWS_INSTALLED'

[IO.File]::WriteAllText("$base\release_gpu_keep_api.bat","@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File %~dp0scripts\release_gpu.ps1`r`n",[Text.Encoding]::ASCII)
