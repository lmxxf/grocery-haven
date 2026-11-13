Get-Content 'C:\Program Files (x86)\Steam\logs\gameprocess_log.txt' -Tail 60 -ErrorAction SilentlyContinue
Get-Content 'C:\Program Files (x86)\Steam\logs\console_log.txt' -Tail 15 -ErrorAction SilentlyContinue
Get-ChildItem 'D:\SteamLibrary\steamapps\common\PBZ\platform\steam' | Select-Object Name,Length
Get-Process PBZ -ErrorAction SilentlyContinue | Select-Object *
