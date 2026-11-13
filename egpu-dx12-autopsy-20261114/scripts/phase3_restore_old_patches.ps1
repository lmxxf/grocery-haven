# Optional rollback to the PRE-TEST OptiScaler/DLSS5 stack. Not used by cleanup.
$ErrorActionPreference='Stop'
$backup='C:\Temp\egpu_backup'
$game='D:\SteamLibrary\steamapps\common\PBZ\platform\steam'
if(Get-Process PBZ -ErrorAction SilentlyContinue){throw 'Close PBZ before restoring patches'}
$manifest=Get-Content "$backup\PBZ_thirdparty_manifest.json" -Raw | ConvertFrom-Json
foreach($f in $manifest){if((Get-FileHash (Join-Path "$backup\PBZ_thirdparty" $f.Relative)).Hash -ne $f.SHA256){throw "Backup hash mismatch: $($f.Relative)"}}
$items=Get-ChildItem "$backup\PBZ_thirdparty" -Force
foreach($item in $items){if(Test-Path (Join-Path $game $item.Name)){throw "Target already exists: $($item.Name). Nothing restored."}}
foreach($item in $items){Copy-Item $item.FullName $game -Recurse}
Copy-Item "$backup\PBZ_GameUserSettings.original.ini" 'C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows\GameUserSettings.ini' -Force
foreach($f in $manifest){if((Get-FileHash (Join-Path $game $f.Relative)).Hash -ne $f.SHA256){throw "Restored hash mismatch: $($f.Relative)"}}
"Restored and verified $($manifest.Count) old patch files plus original INI; backup retained."
