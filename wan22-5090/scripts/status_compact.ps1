$base='C:\AI\Wan22-ComfyUI';$s=@{time=(Get-Date).ToString('o')}
foreach($n in @('bootstrap','acceleration')){if(Test-Path "$base\logs\${n}_status.json"){$s[$n]=Get-Content "$base\logs\${n}_status.json" -Raw | ConvertFrom-Json}}
if(Test-Path "$base\logs\model_download_status.json"){$m=Get-Content "$base\logs\model_download_status.json" -Raw | ConvertFrom-Json;$s.models=@{state=$m.state;verified=@($m.verified | ForEach-Object {$_.file});active=$m.active;pending=$m.pending;error=$m.error}}
$progress=@{};Get-ChildItem "$base\logs\*.download.out.log" -ErrorAction SilentlyContinue | ForEach-Object {$line=Get-Content $_.FullName -Tail 20 | Where-Object {$_ -match 'DL:'} | Select-Object -Last 1;if($line){$progress[$_.Name]=$line.Trim()}};$s.download_progress=$progress
$s.gpu_smoke=(Test-Path "$base\logs\gpu_smoke.json");$s.attention_benchmark=(Test-Path "$base\logs\attention_benchmark.json")
$s | ConvertTo-Json -Depth 7 -Compress
