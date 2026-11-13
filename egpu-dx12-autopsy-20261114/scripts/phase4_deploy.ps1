$ErrorActionPreference='Stop'
$p=Get-Process b1,b1-Win64-Shipping -ErrorAction SilentlyContinue
if($p){try{$p|Wait-Process -Timeout 15 -ErrorAction Stop}catch{$p|Stop-Process -Force;$p|Wait-Process -Timeout 15}}
$game='D:\SteamLibrary\steamapps\common\BlackMythWukong\b1\Binaries\Win64'
if(Test-Path "$game\egpu_booster.log"){Copy-Item "$game\egpu_booster.log" 'C:\Temp\egpu_probe\phase4_initial_capture.log';Remove-Item "$game\egpu_booster.log"}
Copy-Item 'C:\Temp\egpu_probe\dxgi.dll' "$game\dxgi.dll" -Force
Copy-Item 'C:\Users\seth\AppData\Local\b1\Saved\Config\Windows\GameUserSettings.ini' 'C:\Temp\egpu_backup\phase4\wukong_test_settings.ini'
