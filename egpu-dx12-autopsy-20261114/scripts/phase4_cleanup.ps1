$ErrorActionPreference='Stop'
$base='C:\Temp\egpu_backup\phase4\pbz'
$report='C:\Temp\egpu_probe\phase4\cleanup';New-Item -ItemType Directory -Force $report|Out-Null
New-Item -ItemType File -Force 'C:\Temp\egpu_probe\motion_stop'|Out-Null
Start-Sleep -Seconds 1
$manifest=Get-Content "$base\backup_hashes.json" -Raw|ConvertFrom-Json
foreach($f in $manifest){if((Get-FileHash (Join-Path $base $f.Relative)).Hash -ne $f.SHA256){throw "Backup integrity failure $($f.Relative)"}}
$roots=@('D:\SteamLibrary\steamapps\common\PBZ','D:\SteamLibrary\steamapps\common\BlackMythWukong')
foreach($root in $roots){$related=Get-CimInstance Win32_Process|Where-Object {$_.ExecutablePath -like "$root\*"};foreach($p in $related){Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue};foreach($p in $related){Wait-Process -Id $p.ProcessId -Timeout 20 -ErrorAction SilentlyContinue}}
$pbz=$roots[0]+'\platform\steam';$wukong=$roots[1]+'\b1\Binaries\Win64'
$used='D:\Temp\egpu_backup\phase4_used_proxy';New-Item -ItemType Directory -Force $used|Out-Null
foreach($dir in @($pbz,$wukong)){
 $tag=if($dir -eq $pbz){'pbz'}else{'wukong'}
 if(Test-Path "$dir\egpu_booster.log"){Copy-Item "$dir\egpu_booster.log" "$report\${tag}_final.full.log"}
 foreach($file in @(Get-ChildItem $dir -File|Where-Object {$_.Name -eq 'dxgi.dll' -or $_.Name -like 'dxgi.phase4_old_*.disabled'})){
  try{Remove-Item $file.FullName -Force}catch{Move-Item $file.FullName (Join-Path $used ($tag+'.'+$file.Name+'.'+[DateTime]::UtcNow.Ticks))}
 }
 Remove-Item "$dir\egpu_booster.ini","$dir\egpu_booster.log" -ErrorAction SilentlyContinue
}
function RestoreFolder($src,$dst,$archive){
 if(-not(Test-Path $src)){throw "Missing restore source $src"}
 if(Test-Path $dst){Copy-Item $dst $archive -Recurse;Remove-Item $dst -Recurse -Force}
 New-Item -ItemType Directory -Force $dst|Out-Null
 Get-ChildItem $src -Force|Copy-Item -Destination $dst -Recurse -Force
}
$cfg='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows'
$save=$roots[0]+'\ProjectPBZ\Saved'
$nlp='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\ProfileNLP'
RestoreFolder "$base\config" $cfg "$report\pbz_config_after_test"
RestoreFolder "$base\SaveGames" "$save\SaveGames" "$report\pbz_SaveGames_after_test"
RestoreFolder "$base\ProfileNLP" $nlp "$report\pbz_ProfileNLP_after_test"
Get-ChildItem $base -Filter '*.sav' -File|ForEach-Object{Copy-Item $_.FullName (Join-Path $save $_.Name) -Force}
foreach($f in $manifest){
 $relative=$f.Relative;$parts=$relative -split '\\',2
 if($parts[0] -eq 'config'){$target=Join-Path $cfg $parts[1]}
 elseif($parts[0] -eq 'SaveGames'){$target=Join-Path "$save\SaveGames" $parts[1]}
 elseif($parts[0] -eq 'ProfileNLP'){$target=Join-Path $nlp $parts[1]}
 else{$target=Join-Path $save $relative}
 if((Get-FileHash $target).Hash -ne $f.SHA256){throw "Restored hash mismatch $relative"}
}
$wkcfg='C:\Users\seth\AppData\Local\b1\Saved\Config\Windows'
Copy-Item 'C:\Temp\egpu_backup\phase4\wukong_config\*' $wkcfg -Recurse -Force
$wkcount=0;foreach($f in Get-ChildItem 'C:\Temp\egpu_backup\phase4\wukong_config' -File -Recurse){$rel=$f.FullName.Substring('C:\Temp\egpu_backup\phase4\wukong_config\'.Length);if((Get-FileHash $f.FullName).Hash -ne (Get-FileHash (Join-Path $wkcfg $rel)).Hash){throw "Wukong restore mismatch $rel"};$wkcount++}
[pscustomobject]@{PBZProcesses=@(Get-Process PBZ -ErrorAction SilentlyContinue).Count;WukongProcesses=@(Get-Process b1,b1-Win64-Shipping -ErrorAction SilentlyContinue).Count;PBZProxyPresent=(Test-Path "$pbz\dxgi.dll");WukongProxyPresent=(Test-Path "$wukong\dxgi.dll");PBZRestoredFiles=$manifest.Count;WukongConfigRestoredFiles=$wkcount;AllRestoreHashesMatch=$true}|ConvertTo-Json|Set-Content -Encoding UTF8 "$report\restore_status.json"
Get-ChildItem $pbz -Force|Select-Object Name,Length|ConvertTo-Json|Set-Content -Encoding UTF8 "$report\pbz_directory.json"
Get-ChildItem $wukong -Force|Select-Object Name,Length|ConvertTo-Json|Set-Content -Encoding UTF8 "$report\wukong_directory.json"
New-Item -ItemType File -Force 'C:\Temp\egpu_probe\desktop_stop'|Out-Null
'cleanup_and_restore_verified=1'
