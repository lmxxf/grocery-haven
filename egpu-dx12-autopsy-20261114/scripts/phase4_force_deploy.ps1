$ErrorActionPreference='Stop'
$root='D:\SteamLibrary\steamapps\common\BlackMythWukong'
$game="$root\b1\Binaries\Win64"
$related=Get-CimInstance Win32_Process | Where-Object {$_.ExecutablePath -like "$root\*"}
foreach($p in $related){Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue}
foreach($p in $related){Wait-Process -Id $p.ProcessId -Timeout 20 -ErrorAction SilentlyContinue}
if(Test-Path "$game\dxgi.dll"){
 if((Get-FileHash "$game\dxgi.dll").Hash -ne (Get-FileHash 'C:\Temp\egpu_probe\dxgi.dll').Hash){
  Rename-Item "$game\dxgi.dll" ("dxgi.phase4_old_"+[DateTime]::UtcNow.Ticks+".disabled")
  Copy-Item 'C:\Temp\egpu_probe\dxgi.dll' "$game\dxgi.dll"
 }
}else{Copy-Item 'C:\Temp\egpu_probe\dxgi.dll' "$game\dxgi.dll"}
if((Get-FileHash "$game\dxgi.dll").Hash -ne (Get-FileHash 'C:\Temp\egpu_probe\dxgi.dll').Hash){throw 'Deployment hash mismatch'}
Copy-Item 'C:\Users\seth\AppData\Local\b1\Saved\Config\Windows\GameUserSettings.ini' 'C:\Temp\egpu_backup\phase4\wukong_test_settings.ini' -Force
if(Test-Path "$game\egpu_booster.log"){Copy-Item "$game\egpu_booster.log" 'C:\Temp\egpu_probe\phase4_initial_capture.log' -Force;Remove-Item "$game\egpu_booster.log"}
Get-FileHash "$game\dxgi.dll" | Format-List
'final_v03_deployed=1'
