param([string]$Label,[int]$Seconds=60)
$ErrorActionPreference='Stop'
$dest="C:\Temp\egpu_probe\phase3\$Label"
New-Item -ItemType Directory -Force $dest | Out-Null
$log='D:\SteamLibrary\steamapps\common\PBZ\platform\steam\egpu_booster.log'
$startBytes=if(Test-Path $log){(Get-Item $log).Length}else{0}
$start=[DateTime]::UtcNow.ToString('o')
Get-Process PBZ -ErrorAction SilentlyContinue | Select-Object Id,SessionId,StartTime,CPU | ConvertTo-Json | Set-Content "$dest\process_start.json"
Copy-Item 'D:\SteamLibrary\steamapps\common\PBZ\platform\steam\egpu_booster.ini' "$dest\egpu_booster.ini" -ErrorAction SilentlyContinue
& nvidia-smi -q | Set-Content "$dest\gpu_before.txt"
$query=Start-Process nvidia-smi -ArgumentList '--query-gpu=timestamp,pcie.link.gen.current,pcie.link.width.current,memory.used,utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv -l 1' -NoNewWindow -PassThru -RedirectStandardOutput "$dest\gpu_query.csv" -RedirectStandardError "$dest\gpu_query_stderr.txt"
try {& nvidia-smi dmon -s uct -d 1 -c $Seconds | Set-Content -Encoding ascii "$dest\dmon.txt"}finally{if(-not $query.HasExited){Stop-Process -Id $query.Id -ErrorAction SilentlyContinue}}
$end=[DateTime]::UtcNow.ToString('o')
if(Test-Path $log){
 $f=[IO.File]::Open($log,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 try{$bytes=New-Object byte[] $f.Length;[void]$f.Read($bytes,0,$bytes.Length)}finally{$f.Dispose()}
 [IO.File]::WriteAllBytes("$dest\egpu_booster.full.log",$bytes)
 if($bytes.Length -ge $startBytes){[IO.File]::WriteAllBytes("$dest\egpu_booster.window.log",$bytes[$startBytes..($bytes.Length-1)])}
}
@{label=$Label;startUtc=$start;endUtc=$end;secondsRequested=$Seconds;startLogBytes=$startBytes;endLogBytes=if(Test-Path $log){(Get-Item $log).Length}else{0}} | ConvertTo-Json | Set-Content "$dest\window.json"
Get-Process PBZ -ErrorAction SilentlyContinue | Select-Object Id,SessionId,StartTime,CPU | ConvertTo-Json | Set-Content "$dest\process_end.json"
"collected=$Label"
