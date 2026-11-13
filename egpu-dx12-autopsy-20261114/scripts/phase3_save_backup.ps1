$save='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\SaveGames'
if((Test-Path $save) -and -not(Test-Path 'C:\Temp\egpu_backup\PBZ_SaveGames')){Copy-Item $save 'C:\Temp\egpu_backup\PBZ_SaveGames' -Recurse}
Get-ChildItem $save -Recurse -File -ErrorAction SilentlyContinue | Select-Object FullName,Length | ConvertTo-Json
