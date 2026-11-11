$ErrorActionPreference='Stop';$base='C:\AI\Wan22-ComfyUI';$app="$base\ComfyUI_windows_portable\ComfyUI";$py="$base\ComfyUI_windows_portable\python_embeded\python.exe"
New-Item -ItemType Directory -Force -Path "$base\input","$base\output","$base\temp","$base\user","$base\cache\temp","$base\cache\triton","$base\cache\torch","$base\cache\inductor" | Out-Null
$env:TRITON_DEFAULT_FP_FUSION='1';$env:PYTHONUNBUFFERED='1';$env:PYTHONNOUSERSITE='1';$env:HF_HOME="$base\cache\hf";$env:TORCH_HOME="$base\cache\torch";$env:TRITON_CACHE_DIR="$base\cache\triton";$env:TORCHINDUCTOR_CACHE_DIR="$base\cache\inductor";$env:PIP_CACHE_DIR="$base\cache\pip";$env:TEMP="$base\cache\temp";$env:TMP=$env:TEMP
$ffmpeg=Get-ChildItem "$base\tools\ffmpeg" -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if($ffmpeg){$env:PATH=$ffmpeg.DirectoryName+';'+$env:PATH}
Set-Location $app
$config=Get-Content "$base\server_config.json" -Raw | ConvertFrom-Json
for($attempt=0;$attempt -lt 2;$attempt++){
 $arguments=@('-s',"$app\main.py",'--listen','0.0.0.0','--port','8188','--windows-standalone-build','--disable-auto-launch','--disable-xformers','--reserve-vram','3','--input-directory',"$base\input",'--output-directory',"$base\output",'--temp-directory',"$base\temp",'--user-directory',"$base\user")
 if($config.backend -eq 'sage'){$arguments+='--use-sage-attention'}else{$arguments+='--use-pytorch-cross-attention'}
 $p=Start-Process -FilePath $py -ArgumentList $arguments -WorkingDirectory $app -PassThru -RedirectStandardOutput "$base\logs\comfy_server.out.log" -RedirectStandardError "$base\logs\comfy_server.err.log" -WindowStyle Hidden
 $null=$p.Handle;$p.Id | Set-Content "$base\logs\comfy.pid";@{pid=$p.Id;backend=$config.backend;started=(Get-Date).ToString('o');arguments=$arguments} | ConvertTo-Json -Depth 4 | Set-Content "$base\logs\server_launch.json" -Encoding UTF8
 $p.WaitForExit()
 if($config.backend -eq 'sage' -and $p.ExitCode -ne 0){$config.backend='sdpa';$config | ConvertTo-Json | Set-Content "$base\server_config.json" -Encoding UTF8;Copy-Item "$base\logs\comfy_server.err.log" "$base\logs\sage_startup_failure.log" -Force;continue}
 exit $p.ExitCode
}
exit 1
