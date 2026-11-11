$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$base='C:\AI\Wan22-ComfyUI';New-Item -ItemType Directory -Force -Path "$base\tools","$base\tools\aria2","$base\downloads","$base\logs" | Out-Null
function Get-Download($url,$dest){
 $stem=[IO.Path]::GetFileName($dest)
 $args=@('-sS','-L','--fail','--http1.1','--retry','8','--retry-all-errors','--retry-delay','3','--proxy','http://192.168.31.198:17891','--connect-timeout','30','-o',$dest,$url)
 $p=Start-Process -FilePath 'C:\Windows\System32\curl.exe' -ArgumentList $args -Wait -PassThru -RedirectStandardOutput "$base\logs\curl_$stem.out.log" -RedirectStandardError "$base\logs\curl_$stem.err.log"
 if($p.ExitCode -ne 0){throw "Download failed $url code=$($p.ExitCode)"}
}
Get-Download 'https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip' "$base\downloads\aria2.zip"
Expand-Archive -Path "$base\downloads\aria2.zip" -DestinationPath "$base\tools\aria2" -Force
Get-Download 'https://github.com/ip7z/7zip/releases/download/26.06/7zr.exe' "$base\tools\7zr.exe"
$actual=(Get-FileHash "$base\tools\7zr.exe" -Algorithm SHA256).Hash.ToLower()
if($actual -ne 'e80db2dad715a6c5adabe292d31ed54e11f4e9b99ca349827b50573b175891bc'){throw '7zr integrity mismatch'}
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $base\scripts\download_models.ps1"
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Days 2) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'Wan22-Download-Models' -Action $action -User 'SYSTEM' -RunLevel Highest -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'Wan22-Download-Models'
$aria=(Get-ChildItem "$base\tools\aria2" -Filter aria2c.exe -Recurse | Select-Object -First 1).FullName
$oldEap=$ErrorActionPreference;$ErrorActionPreference='Continue'
& $aria --all-proxy=http://192.168.31.198:17891 -c -x8 -s8 --min-split-size=16M --file-allocation=none --max-tries=20 --retry-wait=5 --console-log-level=warn --summary-interval=30 '--checksum=sha-256=7170c2db49c182a81adcc051e80234f99dd891656fb200737f87797876348f96' "--dir=$base\downloads" --out=ComfyUI_windows_portable_nvidia.7z 'https://github.com/Comfy-Org/ComfyUI/releases/download/v0.44.0/ComfyUI_windows_portable_nvidia.7z'
$code=$LASTEXITCODE;$ErrorActionPreference=$oldEap
if($code -ne 0){throw 'Portable download failed'}
& "$base\tools\7zr.exe" x "$base\downloads\ComfyUI_windows_portable_nvidia.7z" "-o$base" -y
if($LASTEXITCODE -ne 0){throw 'Portable extraction failed'}
$py="$base\ComfyUI_windows_portable\python_embeded\python.exe"
& $py -s -c "import torch,sys,json; print(json.dumps({'python':sys.version,'torch':torch.__version__,'cuda':torch.version.cuda,'architectures':torch.cuda.get_arch_list(),'capability':torch.cuda.get_device_capability(0),'gpu':torch.cuda.get_device_name(0)}))" | Tee-Object "$base\logs\torch_inventory.json"
if($LASTEXITCODE -ne 0){throw 'Torch GPU check failed'}
Get-Download 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' "$base\downloads\ffmpeg.zip"
Expand-Archive -Path "$base\downloads\ffmpeg.zip" -DestinationPath "$base\tools\ffmpeg" -Force
'BOOTSTRAP_COMPLETE' | Set-Content "$base\logs\bootstrap_complete.txt"
