$ErrorActionPreference='Stop'
$backup='C:\Temp\egpu_backup\phase4'
$game='D:\SteamLibrary\steamapps\common\BlackMythWukong\b1\Binaries\Win64'
New-Item -ItemType Directory -Force $backup | Out-Null
if(-not(Test-Path "$backup\wukong_config")){
 Copy-Item 'C:\Users\seth\AppData\Local\b1\Saved\Config\Windows' "$backup\wukong_config" -Recurse
 Get-ChildItem $game -Force | Select-Object Name,Length,LastWriteTime | ConvertTo-Json | Set-Content "$backup\wukong_original_directory.json"
 if(Test-Path "$game\dxgi.dll"){throw 'Unexpected pre-existing Wukong dxgi.dll; stop and inspect'}
}
Copy-Item 'C:\Temp\egpu_probe\dxgi.dll' "$game\dxgi.dll" -Force
@"
[booster]
enabled=1
mode=0
profile_cpu=1
"@ | Set-Content -Encoding ascii "$game\egpu_booster.ini"
