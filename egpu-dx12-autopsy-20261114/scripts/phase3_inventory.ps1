$ErrorActionPreference='Stop'
$root='D:\SteamLibrary\steamapps'
Get-ChildItem "$root\appmanifest_*.acf" | ForEach-Object {$content=Get-Content $_.FullName -Raw;if($content -match 'PBZ|BlackMythWukong'){Write-Output "MANIFEST $($_.FullName)`n$content"}}
$pbz="$root\common\PBZ\platform\steam"
Get-ChildItem $pbz -Force | Select-Object Name,Length,LastWriteTime,Mode | ConvertTo-Json -Depth 3
Get-ChildItem "$root\common\PBZ" -Filter '*.exe' -Recurse | Select-Object FullName,Length | ConvertTo-Json
Get-ChildItem "$root\common\BlackMythWukong" -Filter '*.exe' -Recurse | Select-Object FullName,Length | ConvertTo-Json
$ini='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows\GameUserSettings.ini'
Write-Output "SETTINGS $ini";if(Test-Path $ini){Get-Content $ini}
Write-Output 'DMON_TEST'
& nvidia-smi dmon -s uct -d 1 -c 2
Write-Output 'PCIE_QUERY_TEST'
& nvidia-smi --query-gpu=pcie.link.gen.current,pcie.link.width.current,memory.used,utilization.gpu --format=csv
