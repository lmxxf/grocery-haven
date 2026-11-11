$base='C:\AI\Wan22-ComfyUI'
foreach($name in @('wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors','wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors','wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors')){Write-Output $name;Get-Content "$base\logs\$name.download.out.log" -Tail 6}
Get-Process aria2c,powershell -ErrorAction SilentlyContinue | Sort-Object CPU -Descending | Select-Object -First 5 Id,ProcessName,CPU,WorkingSet64 | ConvertTo-Json
