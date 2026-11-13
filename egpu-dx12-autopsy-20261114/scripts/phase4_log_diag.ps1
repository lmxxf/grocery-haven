$logs='C:\Users\seth\AppData\Local\b1\Saved\Logs'
Get-ChildItem $logs -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,Length,LastWriteTime | Format-Table
Get-ChildItem $logs -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object {Get-Content $_.FullName -Tail 60}
Get-Content 'D:\SteamLibrary\steamapps\common\BlackMythWukong\b1\Binaries\Win64\egpu_booster.log' -Tail 100 | Select-String 'cpu_thread|cpu_breakdown'
