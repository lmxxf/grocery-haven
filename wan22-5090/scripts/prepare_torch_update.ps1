$base='C:\AI\Wan22-ComfyUI'
try {$q=Invoke-RestMethod 'http://127.0.0.1:8188/queue' -TimeoutSec 3;if($q.queue_running.Count -gt 0 -or $q.queue_pending.Count -gt 0){throw 'Queue busy'}} catch {if($_.Exception.Message -eq 'Queue busy'){throw}}
if(Get-ScheduledTask -TaskName 'Wan22-ComfyUI' -ErrorAction SilentlyContinue){Stop-ScheduledTask -TaskName 'Wan22-ComfyUI'}
if(Test-Path "$base\logs\comfy.pid"){$id=[int](Get-Content "$base\logs\comfy.pid");$p=Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue;if($p -and $p.ExecutablePath -like "$base\*"){Stop-Process -Id $id -Force}}
foreach($n in @('gpu_smoke.json','attention_benchmark.json')){if(Test-Path "$base\logs\$n"){Move-Item "$base\logs\$n" "$base\logs\baseline_2_14_$n" -Force}}
Start-ScheduledTask -TaskName 'Wan22-Acceleration'
