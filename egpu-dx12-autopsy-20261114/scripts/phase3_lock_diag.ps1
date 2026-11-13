$target='D:\SteamLibrary\steamapps\common\PBZ\platform\steam\dxgi.dll'
Get-Process | ForEach-Object {try{$p=$_;$hits=$p.Modules | Where-Object {$_.FileName -eq $target};if($hits){[pscustomobject]@{Id=$p.Id;Name=$p.Name;Path=$p.Path;SessionId=$p.SessionId}}}catch{}} | ConvertTo-Json
Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*PBZ*'} | Select-Object Name,ProcessId,ParentProcessId,CommandLine | ConvertTo-Json
Get-FileHash $target,'C:\Temp\egpu_probe\dxgi.dll' | Format-List
