Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'PBZ.exe'} | Select-Object ProcessId,ParentProcessId,SessionId,CreationDate,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3
Get-Process PBZ -ErrorAction SilentlyContinue | Select-Object Id,CPU,StartTime,Responding,MainWindowHandle,MainWindowTitle,WorkingSet64 | ConvertTo-Json
Get-CimInstance Win32_VideoController | Select-Object Name,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate | ConvertTo-Json
Get-Content 'C:\Program Files (x86)\Steam\logs\console_log.txt' -Tail 20 -ErrorAction SilentlyContinue
