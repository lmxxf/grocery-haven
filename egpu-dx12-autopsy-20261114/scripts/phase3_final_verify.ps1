$ErrorActionPreference='Stop'
$game='D:\SteamLibrary\steamapps\common\PBZ\platform\steam'
$ini='C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows\GameUserSettings.ini'
[pscustomobject]@{
 PBZProcesses=@(Get-Process PBZ -ErrorAction SilentlyContinue).Count
 ProxyPresent=(Test-Path "$game\dxgi.dll")
 TestIniPresent=(Test-Path "$game\egpu_booster.ini")
 TestLogPresent=(Test-Path "$game\egpu_booster.log")
 OriginalIniRestored=((Get-FileHash $ini).Hash -eq (Get-FileHash 'C:\Temp\egpu_backup\PBZ_GameUserSettings.original.ini').Hash)
 TaskPresent=([bool](Get-ScheduledTask -TaskName 'eGPU-Phase3-Desktop' -ErrorAction SilentlyContinue))
 TemporaryProxySHA256=(Get-FileHash 'C:\Temp\egpu_probe\dxgi.dll').Hash
} | ConvertTo-Json
Get-ChildItem $game -Force | Select-Object Name,Length | ConvertTo-Json
