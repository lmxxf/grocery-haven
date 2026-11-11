$base='C:\AI\Wan22-ComfyUI'
Get-ChildItem "$base\downloads" | Select-Object Name,Length | ConvertTo-Json
if(Test-Path "$base\logs\bootstrap_error.log"){Get-Content "$base\logs\bootstrap_error.log" -Tail 30}
if(Test-Path "$base\logs\bootstrap.log"){Get-Content "$base\logs\bootstrap.log" -Tail 10}
Get-ScheduledTask -TaskName 'Wan22-*' | Select-Object TaskName,State | ConvertTo-Json
