$ErrorActionPreference='Stop'
$game='D:\SteamLibrary\steamapps\common\PBZ\platform\steam'
$backup='C:\Temp\egpu_backup'
$dest='C:\Temp\egpu_probe\phase3\cleanup'
New-Item -ItemType Directory -Force $dest | Out-Null
$old=Get-Process PBZ -ErrorAction SilentlyContinue
if($old){$old|Stop-Process;$old|Wait-Process -Timeout 20}
if(Test-Path "$game\egpu_booster.log"){Copy-Item "$game\egpu_booster.log" "$dest\wide_final.log"}
foreach($name in @('dxgi.dll','egpu_booster.ini','egpu_booster.log')){if(Test-Path "$game\$name"){Remove-Item "$game\$name" -Force}}
$settings='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows\GameUserSettings.ini'
Copy-Item "$backup\PBZ_GameUserSettings.original.ini" $settings -Force
if((Get-FileHash $settings).Hash -ne (Get-FileHash "$backup\PBZ_GameUserSettings.original.ini").Hash){throw 'INI restore hash mismatch'}
# The tests only loaded the original checkpoint and changed VSync. Preserve the pre-test SaveGames snapshot.
$save='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\SaveGames'
if(Test-Path "$backup\PBZ_SaveGames"){
 Copy-Item $save "$dest\SaveGames_after_test" -Recurse
 Copy-Item "$backup\PBZ_SaveGames\*" $save -Recurse -Force
}
$manifest=Get-Content "$backup\PBZ_thirdparty_manifest.json" -Raw | ConvertFrom-Json
foreach($f in $manifest){if((Get-FileHash (Join-Path "$backup\PBZ_thirdparty" $f.Relative)).Hash -ne $f.SHA256){throw "Backup verification failed $($f.Relative)"}}
Get-ChildItem $game -Force | Select-Object Name,Length | ConvertTo-Json | Set-Content "$dest\clean_directory.json"
Get-FileHash $settings | Format-List | Out-File "$dest\restored_settings_hash.txt"
"cleanup_complete original_ini_restored=1 old_patch_backup_verified=$($manifest.Count) proxy_removed=1" | Set-Content "$dest\status.txt"
New-Item -ItemType File -Force 'C:\Temp\egpu_probe\desktop_stop' | Out-Null
