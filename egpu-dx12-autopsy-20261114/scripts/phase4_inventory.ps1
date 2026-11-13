$game='D:\SteamLibrary\steamapps\common\BlackMythWukong\b1\Binaries\Win64'
Get-ChildItem $game -Force | Select-Object Name,Length,LastWriteTime | ConvertTo-Json
foreach($root in @('C:\Users\seth\AppData\Local\b1','C:\Users\seth\AppData\Local\ProjectPBZ')){
 "ROOT $root"
 Get-ChildItem "$root\Saved\Config" -File -Recurse -ErrorAction SilentlyContinue | Select-Object FullName,Length | ConvertTo-Json
 Get-ChildItem "$root\Saved" -Directory -ErrorAction SilentlyContinue | Select-Object Name | ConvertTo-Json
}
Get-Content 'C:\Users\seth\AppData\Local\b1\Saved\Config\Windows\GameUserSettings.ini' -ErrorAction SilentlyContinue
