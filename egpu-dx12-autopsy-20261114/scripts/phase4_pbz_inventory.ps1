$root='D:\SteamLibrary\steamapps\common\PBZ'
foreach($p in @("$root\ProjectPBZ\Saved","$root\Saved",'C:\Users\seth\AppData\Local\ProjectPBZ\Saved\ProfileNLP')){if(Test-Path $p){"PATH $p";Get-ChildItem $p -Force | Select-Object Name,Length,Mode | ConvertTo-Json}}
Get-ChildItem 'C:\Program Files (x86)\Steam\userdata' -Directory | ForEach-Object {$remote=Join-Path $_.FullName '4115450';if(Test-Path $remote){"STEAM $remote";Get-ChildItem $remote -Recurse -File | Select-Object FullName,Length | ConvertTo-Json}}
