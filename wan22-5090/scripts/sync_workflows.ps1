$base='C:\AI\Wan22-ComfyUI'
Copy-Item "$base\scripts\Wan22_T2V_20steps_FP8.json","$base\scripts\Wan22_I2V_20steps_FP8.json" "$base\user\default\workflows" -Force
Copy-Item "$base\scripts\wan22_t2v_20steps_api.json","$base\scripts\wan22_i2v_20steps_api.json" "$base\workflows" -Force
