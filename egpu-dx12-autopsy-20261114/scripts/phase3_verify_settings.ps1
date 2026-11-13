$ini='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows\GameUserSettings.ini'
Get-Content $ini | Select-String 'bUseVSync|FrameRateLimit|ResolutionSize|FullscreenMode'
Get-Content 'D:\SteamLibrary\steamapps\common\PBZ\platform\steam\egpu_booster.log' -TotalCount 30
