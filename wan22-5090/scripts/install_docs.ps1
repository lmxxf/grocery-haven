$base='C:\AI\Wan22-ComfyUI'
Copy-Item "$base\scripts\README.md","$base\scripts\results.json","$base\scripts\deployment_acceptance.json" $base -Force
Get-ScheduledTask -TaskName 'Wan22-ComfyUI' | Select-Object TaskName,State | ConvertTo-Json
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
@('README.md','results.json','deployment_acceptance.json') | ForEach-Object {(Get-FileHash "$base\$_" -Algorithm SHA256) | Select-Object Path,Hash} | ConvertTo-Json
