$ErrorActionPreference='Stop'
$game='D:\SteamLibrary\steamapps\common\PBZ\platform\steam'
$backup='C:\Temp\egpu_backup'
New-Item -ItemType Directory -Force $backup | Out-Null
$third=Join-Path $backup 'PBZ_thirdparty'
if(Test-Path $third){throw 'Backup exists; refusing to overwrite original backup'}
New-Item -ItemType Directory $third | Out-Null
# Leave the shipped executable, Steam API, TBB and native D3D12 runtime untouched.
$native=@('PBZ.exe','steam_api64.dll','tbbmalloc.dll','D3D12')
$items=Get-ChildItem $game -Force | Where-Object {$_.Name -notin $native}
$manifest=@()
foreach($item in $items){
 $files=if($item.PSIsContainer){Get-ChildItem $item.FullName -File -Recurse -Force}else{@($item)}
 foreach($file in $files){$manifest+= [pscustomobject]@{Relative=$file.FullName.Substring($game.Length+1);Length=$file.Length;LastWriteTimeUtc=$file.LastWriteTimeUtc.ToString('o');SHA256=(Get-FileHash $file.FullName -Algorithm SHA256).Hash}}
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 "$backup\PBZ_thirdparty_manifest.json"
$ini='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows\GameUserSettings.ini'
Copy-Item $ini "$backup\PBZ_GameUserSettings.original.ini"
$config=Split-Path $ini
Copy-Item $config "$backup\PBZ_Config_Windows" -Recurse
foreach($item in $items){Move-Item $item.FullName $third}
foreach($file in $manifest){$path=Join-Path $third $file.Relative;if((Get-FileHash $path -Algorithm SHA256).Hash -ne $file.SHA256){throw "Backup hash mismatch $path"}}
$text=Get-Content $ini -Raw
$text=$text -replace '(?m)^FrameRateLimit_WhenBackgrounded=.*$','FrameRateLimit_WhenBackgrounded=0.000000'
$text=$text -replace '(?m)^bUseVSync=.*$','bUseVSync=False'
[IO.File]::WriteAllText($ini,$text,(New-Object Text.UTF8Encoding($false)))
Copy-Item $ini "$backup\PBZ_GameUserSettings.test.ini"
Get-ChildItem $game -Force | Select-Object Name,Length | ConvertTo-Json | Set-Content "$backup\PBZ_clean_directory.json"
Write-Output "Backed up $($manifest.Count) files with SHA256; original settings and complete Config\Windows preserved"
