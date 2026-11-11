$base='C:\AI\Wan22-ComfyUI'
Get-ScheduledTask -TaskName 'Wan22-ComfyUI' -ErrorAction SilentlyContinue | Select-Object TaskName,State | ConvertTo-Json
foreach($n in @('comfy_server.err.log','comfy_server.out.log')){if(Test-Path "$base\logs\$n"){Write-Output $n;Get-Content "$base\logs\$n" -Tail 14}}
