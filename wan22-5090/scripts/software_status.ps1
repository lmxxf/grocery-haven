$base='C:\AI\Wan22-ComfyUI'
foreach($n in @('bootstrap_status.json','acceleration_status.json','gpu_smoke.json','attention_benchmark.json')){if(Test-Path "$base\logs\$n"){Write-Output $n;Get-Content "$base\logs\$n" -Raw}}
foreach($n in @('torch_update.out.log','torch_update.err.log','triton_install.err.log','sage_install.err.log','attention_benchmark.err.log')){if(Test-Path "$base\logs\$n"){Write-Output $n;Get-Content "$base\logs\$n" -Tail 3}}
