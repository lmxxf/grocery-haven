Stop-ScheduledTask -TaskName 'Wan22-Download-Models'
Get-CimInstance Win32_Process -Filter "name='aria2c.exe'" | Where-Object {$_.CommandLine -like '*Wan22-ComfyUI*\models\*'} | ForEach-Object {Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}
Start-ScheduledTask -TaskName 'Wan22-Download-Models'
Get-ScheduledTask -TaskName 'Wan22-Download-Models' | Select-Object TaskName,State | ConvertTo-Json
