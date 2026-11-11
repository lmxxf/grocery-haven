param([ValidateSet('sdpa','sage')][string]$Backend)
$ErrorActionPreference='Stop';$base='C:\AI\Wan22-ComfyUI'
$configFile="$base\server_config.json";$current=$null
if(Test-Path $configFile){$current=Get-Content $configFile -Raw | ConvertFrom-Json}
if(-not $Backend){$Backend=if($current){$current.backend}else{'sdpa'}}
$online=$false
try {$stats=Invoke-RestMethod 'http://127.0.0.1:8188/system_stats' -TimeoutSec 3;$online=$true}catch{}
if($online -and $current.backend -eq $Backend){Write-Output "Already running backend=$Backend";exit 0}
if($online){$q=Invoke-RestMethod 'http://127.0.0.1:8188/queue';if($q.queue_running.Count -gt 0 -or $q.queue_pending.Count -gt 0){throw 'ComfyUI queue is busy; refusing to restart an active generation'}}
$isAdmin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(-not $isAdmin){$elevated=Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File $base\scripts\start_service.ps1 -Backend $Backend" -PassThru -Wait;exit $elevated.ExitCode}
if(Get-ScheduledTask -TaskName 'Wan22-ComfyUI' -ErrorAction SilentlyContinue){Stop-ScheduledTask -TaskName 'Wan22-ComfyUI'}
if(Test-Path "$base\logs\comfy.pid"){
 $pidFile=[int](Get-Content "$base\logs\comfy.pid");$process=Get-CimInstance Win32_Process -Filter "ProcessId=$pidFile" -ErrorAction SilentlyContinue
 if($process -and $process.ExecutablePath -like "$base\*" -and $process.CommandLine -like '*main.py*'){Stop-Process -Id $pidFile -Force}
}
Start-Sleep -Milliseconds 300
$archive="$base\logs\history";New-Item -ItemType Directory -Force -Path $archive | Out-Null
$stamp=(Get-Date).ToString('yyyyMMdd_HHmmss')+'_'+$current.backend
foreach($n in @('comfy_server.out.log','comfy_server.err.log')){if(Test-Path "$base\logs\$n"){Copy-Item "$base\logs\$n" "$archive\${stamp}_$n" -Force}}
@{backend=$Backend;listen='0.0.0.0';port=8188} | ConvertTo-Json | Set-Content $configFile -Encoding UTF8
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $base\scripts\run_server.ps1" -WorkingDirectory $base
$trigger=New-ScheduledTaskTrigger -AtStartup
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Wan22-ComfyUI' -Action $action -Trigger $trigger -User 'SYSTEM' -RunLevel Highest -Settings $settings -Force | Out-Null
if(-not(Get-NetFirewallRule -Name 'Wan22-ComfyUI-LAN-8188' -ErrorAction SilentlyContinue)){New-NetFirewallRule -Name 'Wan22-ComfyUI-LAN-8188' -DisplayName 'Wan22 ComfyUI LAN TCP8188' -Direction Inbound -Protocol TCP -LocalPort 8188 -RemoteAddress '192.168.31.0/24' -Profile Any -Action Allow | Out-Null}
Start-ScheduledTask -TaskName 'Wan22-ComfyUI'
Write-Output "Started backend=$Backend URL=http://192.168.31.50:8188"
