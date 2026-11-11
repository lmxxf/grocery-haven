$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$base='C:\AI\Wan22-ComfyUI';$py="$base\ComfyUI_windows_portable\python_embeded\python.exe"
$env:HTTP_PROXY='http://192.168.31.198:17891';$env:HTTPS_PROXY=$env:HTTP_PROXY;$env:NO_PROXY='localhost,127.0.0.1,192.168.31.50,192.168.31.198';$env:PIP_CACHE_DIR="$base\cache\pip";$env:TRITON_CACHE_DIR="$base\cache\triton";$env:TORCHINDUCTOR_CACHE_DIR="$base\cache\inductor"
New-Item -ItemType Directory -Force -Path "$base\cache\pip","$base\cache\triton","$base\cache\inductor" | Out-Null
function Python-Run([string[]]$ArgumentList,[string]$Name){
 $p=Start-Process -FilePath $py -ArgumentList $ArgumentList -Wait -PassThru -RedirectStandardOutput "$base\logs\$Name.out.log" -RedirectStandardError "$base\logs\$Name.err.log"
 if($p.ExitCode -ne 0){throw "$Name exit=$($p.ExitCode)"}
}
try {
 while(-not(Test-Path "$base\logs\bootstrap_complete.txt")){Start-Sleep -Seconds 5}
 @{state='running';phase='torch_latest_stable'} | ConvertTo-Json | Set-Content "$base\logs\acceleration_status.json" -Encoding UTF8
 $env:TEMP="$base\cache\temp";$env:TMP=$env:TEMP;New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
 $aria=(Get-ChildItem "$base\tools\aria2" -Filter aria2c.exe -Recurse | Select-Object -First 1).FullName
 $wheel='torch-2.15.0+cu132-cp313-cp313-win_amd64.whl';$wheelHash='7b54774dedca2a1147f1ae47451d9a8a7e88b80665fc505bf6a4f1f427d21e97'
 @{state='running';phase='torch_wheel_download'} | ConvertTo-Json | Set-Content "$base\logs\acceleration_status.json" -Encoding UTF8
 for($retry=0;$retry -lt 12;$retry++){
  $args=@('--all-proxy=http://192.168.31.198:17891','--continue=true','--auto-save-interval=5','--auto-file-renaming=false','--file-allocation=none','-x8','-s8','--min-split-size=16M','--max-tries=20','--retry-wait=3','--console-log-level=warn','--summary-interval=30',"--checksum=sha-256=$wheelHash","--dir=$base\downloads","--out=$wheel",'https://download-r2.pytorch.org/whl/cu132/torch-2.15.0%2Bcu132-cp313-cp313-win_amd64.whl')
  $p=Start-Process $aria -ArgumentList $args -Wait -PassThru -RedirectStandardOutput "$base\logs\torch_wheel.download.out.log" -RedirectStandardError "$base\logs\torch_wheel.download.err.log"
  if($p.ExitCode -eq 0){break};if($retry -eq 11){throw 'Torch wheel download failed repeatedly'}
 }
 @{state='running';phase='torch_install'} | ConvertTo-Json | Set-Content "$base\logs\acceleration_status.json" -Encoding UTF8
 Python-Run @('-s','-m','pip','install','--upgrade',"$base\downloads\$wheel",'torchvision','torchaudio','--index-url','https://download.pytorch.org/whl/cu132') 'torch_update' 
 Python-Run @('-s',"$base\scripts\gpu_smoke.py") 'gpu_smoke'
 @{state='running';phase='triton_sage'} | ConvertTo-Json | Set-Content "$base\logs\acceleration_status.json" -Encoding UTF8
 $minor=& $py -s -c 'import sys;print(sys.version_info.minor)'
 if($minor -eq '13'){
  $p=Start-Process curl.exe -ArgumentList @('-sS','-L','--fail','--retry','8','--proxy',$env:HTTPS_PROXY,'-o',"$base\downloads\python_headers.zip",'https://github.com/woct0rdho/triton-windows/releases/download/v3.0.0-windows.post1/python_3.13.2_include_libs.zip') -Wait -PassThru -RedirectStandardError "$base\logs\python_headers.err.log"
  if($p.ExitCode -ne 0){throw 'Python headers download failed'}
  Expand-Archive "$base\downloads\python_headers.zip" -DestinationPath "$base\ComfyUI_windows_portable\python_embeded" -Force
 }
 Python-Run @('-s','-m','pip','install','--only-binary=:all:','triton-windows==3.9.0.post30') 'triton_install'
 $p=Start-Process curl.exe -ArgumentList @('-sS','-L','--fail','--retry','8','--proxy',$env:HTTPS_PROXY,'-o',"$base\downloads\sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl",'https://github.com/woct0rdho/SageAttention/releases/download/v2.2.0-windows.post6/sageattention-2.2.0%2Bcu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl') -Wait -PassThru -RedirectStandardError "$base\logs\sage_download.err.log"
 if($p.ExitCode -ne 0){throw 'Sage wheel download failed'}
 Python-Run @('-s','-m','pip','install','--no-deps',"$base\downloads\sageattention-2.2.0+cu130torch2.10.0andhigher.post6-cp310-abi3-win_amd64.whl") 'sage_install'
 Python-Run @('-s',"$base\scripts\attention_benchmark.py") 'attention_benchmark'
 @{state='complete';time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content "$base\logs\acceleration_status.json" -Encoding UTF8
} catch {
 @{state='failed';error=$_.Exception.Message;time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content "$base\logs\acceleration_status.json" -Encoding UTF8
 exit 1
}
