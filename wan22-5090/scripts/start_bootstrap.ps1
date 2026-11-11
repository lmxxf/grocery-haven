$base='C:\AI\Wan22-ComfyUI'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $base\scripts\bootstrap_runner.ps1"
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Days 2) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Wan22-Bootstrap' -Action $action -User 'SYSTEM' -RunLevel Highest -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'Wan22-Bootstrap'
Get-ScheduledTask -TaskName 'Wan22-Bootstrap' | Select-Object TaskName,State | ConvertTo-Json
