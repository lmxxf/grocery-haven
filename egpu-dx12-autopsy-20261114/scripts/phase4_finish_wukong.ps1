$ErrorActionPreference='Stop'
$root='D:\SteamLibrary\steamapps\common\BlackMythWukong';$game="$root\b1\Binaries\Win64"
$related=Get-CimInstance Win32_Process|Where-Object {$_.ExecutablePath -like "$root\*"}
foreach($p in $related){Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue}
foreach($p in $related){Wait-Process -Id $p.ProcessId -Timeout 20 -ErrorAction SilentlyContinue}
$dest='C:\Temp\egpu_probe\phase4\wukong_final';New-Item -ItemType Directory -Force $dest|Out-Null
Copy-Item "$game\egpu_booster.log" "$dest\egpu_booster.full.log" -ErrorAction SilentlyContinue
$used='D:\Temp\egpu_backup\phase4_used_proxy';New-Item -ItemType Directory -Force $used|Out-Null
foreach($f in @(Get-ChildItem $game -File|Where-Object {$_.Name -eq 'dxgi.dll' -or $_.Name -like 'dxgi.phase4_old_*.disabled'})){
 try{Remove-Item $f.FullName -Force}catch{Move-Item $f.FullName (Join-Path $used ($f.Name+'.'+[DateTime]::UtcNow.Ticks))}
}
Remove-Item "$game\egpu_booster.ini","$game\egpu_booster.log" -ErrorAction SilentlyContinue
$config='C:\Users\seth\AppData\Local\b1\Saved\Config\Windows'
Copy-Item 'C:\Temp\egpu_backup\phase4\wukong_config\*' $config -Recurse -Force
foreach($f in Get-ChildItem 'C:\Temp\egpu_backup\phase4\wukong_config' -File){if((Get-FileHash $f.FullName).Hash -ne (Get-FileHash (Join-Path $config $f.Name)).Hash){throw 'Wukong config restore mismatch'}}
'wukong_cleaned_original_config_verified=1'|Set-Content "$dest\cleanup_status.txt"
