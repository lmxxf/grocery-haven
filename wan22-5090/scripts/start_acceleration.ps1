$base='C:\AI\Wan22-ComfyUI'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $base\scripts\install_acceleration.ps1"
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 6) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Wan22-Acceleration' -Action $action -User 'SYSTEM' -RunLevel Highest -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'Wan22-Acceleration'
Get-ScheduledTask -TaskName 'Wan22-Acceleration' | Select-Object TaskName,State | ConvertTo-Json
