param([ValidateSet('disabled','baseline','narrow','wide')][string]$Case='baseline')
$ErrorActionPreference='Stop'
$game='D:\SteamLibrary\steamapps\common\PBZ\platform\steam'
$old=Get-Process PBZ -ErrorAction SilentlyContinue
if($old){$old | Stop-Process; $old | Wait-Process -Timeout 20 -ErrorAction Stop}
Start-Sleep -Milliseconds 500
$dest="C:\Temp\egpu_probe\phase3\startup_$Case"
New-Item -ItemType Directory -Force $dest | Out-Null
if(Test-Path "$game\egpu_booster.log"){Copy-Item "$game\egpu_booster.log" "$dest\previous.log";Remove-Item "$game\egpu_booster.log"}
if(-not(Test-Path "$game\dxgi.dll") -or ((Get-FileHash 'C:\Temp\egpu_probe\dxgi.dll').Hash -ne (Get-FileHash "$game\dxgi.dll").Hash)){Copy-Item 'C:\Temp\egpu_probe\dxgi.dll' "$game\dxgi.dll" -Force}
$enabled=if($Case -eq 'disabled'){0}else{1}
$mode=if($Case -in @('narrow','wide')){1}else{0}
$total=if($Case -eq 'narrow'){20}else{256}
$buf=if($Case -eq 'narrow'){8}else{64}
$heap=if($Case -eq 'narrow'){16}else{128}
@"
[booster]
enabled=$enabled
mode=$mode
min_buffer_kb=4
max_buffer_mb=$buf
min_heap_kb=64
max_heap_mb=$heap
max_total_mb=$total
spoof_heap_properties=0
"@ | Set-Content -Encoding ascii "$game\egpu_booster.ini"
