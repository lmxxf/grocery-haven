$base='C:\AI\Wan22-ComfyUI'
foreach($name in @('wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors','wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors')){
 Write-Output $name
 Get-Content "$base\logs\$name.download.out.log" -Tail 45
 Get-Content "$base\logs\$name.download.err.log" -Tail 10
}
if(Test-Path "$base\logs\torch_update.out.log"){Get-Content "$base\logs\torch_update.out.log" -Tail 7}
if(Test-Path "$base\logs\torch_update.err.log"){Get-Content "$base\logs\torch_update.err.log" -Tail 5}
