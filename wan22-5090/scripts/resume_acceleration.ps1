$base='C:\AI\Wan22-ComfyUI'
Stop-ScheduledTask -TaskName 'Wan22-Acceleration'
Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object {$_.ExecutablePath -like "$base\*" -and $_.CommandLine -like '*pip*install*torch*'} | ForEach-Object {Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}
Start-ScheduledTask -TaskName 'Wan22-Acceleration'
