param([string]$Name)
$ErrorActionPreference='Stop'
$b='C:\AI\Wan22-ComfyUI'
if(Get-ScheduledTask -TaskName 'H3-GPU-Monitor' -ErrorAction SilentlyContinue){Stop-ScheduledTask -TaskName 'H3-GPU-Monitor'}
$p="$b\ComfyUI_windows_portable\python_embeded\python.exe"
$a=New-ScheduledTaskAction -Execute $p -Argument "-s $b\scripts\h3_gpu_monitor.py $b\logs\gpu_$Name.csv"
Register-ScheduledTask -TaskName 'H3-GPU-Monitor' -Action $a -User SYSTEM -RunLevel Highest -Force | Out-Null
Remove-Item "$b\logs\gpu_$Name.csv" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName 'H3-GPU-Monitor'
for($i=0;$i -lt 20;$i++){
 if((Test-Path "$b\logs\gpu_$Name.csv") -and (Get-Item "$b\logs\gpu_$Name.csv").Length -gt 30){return}
 Start-Sleep -Milliseconds 500
}
throw 'GPU sampler did not produce records'
