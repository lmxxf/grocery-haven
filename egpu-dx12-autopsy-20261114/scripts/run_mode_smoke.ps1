param([ValidateSet(0,1)][int]$Mode=0)
$ErrorActionPreference='Stop'
$dir='C:\Temp\egpu_probe'
Set-Location $dir
@"
[booster]
enabled=1
mode=$Mode
min_buffer_kb=4
max_buffer_mb=64
min_heap_kb=64
max_heap_mb=128
max_total_mb=1024
spoof_heap_properties=0
"@ | Set-Content -Encoding ascii egpu_booster.ini
Copy-Item egpu_booster.ini "mode${Mode}.ini" -Force
if (Test-Path egpu_booster.log) { Remove-Item egpu_booster.log }
$p=Start-Process -FilePath "$dir\d3d12_egpu_probe.exe" -WorkingDirectory $dir -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$dir\mode${Mode}_probe.txt" -RedirectStandardError "$dir\mode${Mode}_stderr.txt"
"exit_code=$($p.ExitCode)" | Set-Content -Encoding ascii "mode${Mode}_exit.txt"
if (Test-Path egpu_booster.log) {Copy-Item egpu_booster.log "mode${Mode}_telemetry.log" -Force}
Write-Output "mode=$Mode exit_code=$($p.ExitCode) log_exists=$(Test-Path egpu_booster.log)"
exit $p.ExitCode
