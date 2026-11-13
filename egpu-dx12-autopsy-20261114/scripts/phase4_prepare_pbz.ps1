$ErrorActionPreference='Stop'
$root='D:\SteamLibrary\steamapps\common\PBZ';$game="$root\platform\steam"
$b='C:\Temp\egpu_backup\phase4\pbz';New-Item -ItemType Directory -Force $b|Out-Null
if(-not(Test-Path "$b\config")){
 Copy-Item 'C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows' "$b\config" -Recurse
 Copy-Item "$root\ProjectPBZ\Saved\SaveGames" "$b\SaveGames" -Recurse
 Get-ChildItem "$root\ProjectPBZ\Saved" -Filter '*.sav' -File|Copy-Item -Destination $b
 Copy-Item 'C:\Users\seth\AppData\Local\ProjectPBZ\Saved\ProfileNLP' "$b\ProfileNLP" -Recurse
 Get-ChildItem $b -File -Recurse|ForEach-Object{[pscustomobject]@{Relative=$_.FullName.Substring($b.Length+1);SHA256=(Get-FileHash $_.FullName).Hash}}|ConvertTo-Json|Set-Content "$b\backup_hashes.json"
 if(Test-Path "$game\dxgi.dll"){throw 'Unexpected PBZ proxy before Phase4'}
}
Copy-Item 'C:\Temp\egpu_probe\dxgi.dll' "$game\dxgi.dll" -Force
@"
[booster]
enabled=1
mode=0
profile_cpu=1
track_bindings=0
track_descriptors=0
"@|Set-Content -Encoding ascii "$game\egpu_booster.ini"
