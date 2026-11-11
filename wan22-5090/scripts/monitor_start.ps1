param([string]$Name='sdpa')
$ErrorActionPreference='Stop';$base='C:\AI\Wan22-ComfyUI'
if(Get-ScheduledTask -TaskName 'Wan22-GPU-Monitor' -ErrorAction SilentlyContinue){Stop-ScheduledTask -TaskName 'Wan22-GPU-Monitor'}
$exe=(Get-Command nvidia-smi.exe).Source
$action=New-ScheduledTaskAction -Execute $exe -Argument "--query-gpu=timestamp,memory.used,utilization.gpu,power.draw,temperature.gpu --format=csv,noheader,nounits -lms 500 -f $base\logs\gpu_$Name.csv"
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName 'Wan22-GPU-Monitor' -Action $action -User 'SYSTEM' -RunLevel Highest -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'Wan22-GPU-Monitor'
