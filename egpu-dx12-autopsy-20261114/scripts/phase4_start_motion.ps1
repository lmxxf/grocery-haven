$p=Start-Process powershell.exe -WindowStyle Hidden -PassThru -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File C:\Temp\egpu_probe\phase4_pbz_motion.ps1 -Seconds 70 -Pattern orbit' -RedirectStandardOutput 'C:\Temp\egpu_probe\motion_stdout.txt' -RedirectStandardError 'C:\Temp\egpu_probe\motion_stderr.txt'
"motion_started pid=$($p.Id)"
