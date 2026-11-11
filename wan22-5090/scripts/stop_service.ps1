$ErrorActionPreference='Stop';$base='C:\AI\Wan22-ComfyUI'
$isAdmin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(-not $isAdmin){Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File $base\scripts\stop_service.ps1" -Wait;exit}
if(Get-ScheduledTask -TaskName 'Wan22-ComfyUI' -ErrorAction SilentlyContinue){Stop-ScheduledTask -TaskName 'Wan22-ComfyUI'}
if(Test-Path "$base\logs\comfy.pid"){$pIdValue=[int](Get-Content "$base\logs\comfy.pid");$p=Get-CimInstance Win32_Process -Filter "ProcessId=$pIdValue" -ErrorAction SilentlyContinue;if($p -and $p.ExecutablePath -like "$base\*" -and $p.CommandLine -like '*main.py*'){Stop-Process -Id $pIdValue -Force}}
'ComfyUI stopped; GPU allocations released.'
