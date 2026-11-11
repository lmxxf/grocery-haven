$base='C:\AI\Wan22-ComfyUI'
$old=$ErrorActionPreference;$ErrorActionPreference='Continue'
& "$base\ComfyUI_windows_portable\python_embeded\python.exe" -s "$base\scripts\export_inventory.py"
$code=$LASTEXITCODE;$ErrorActionPreference=$old
if($code -ne 0){exit $code}
Export-ScheduledTask -TaskName 'Wan22-ComfyUI' | Out-File "$base\logs\startup_task.xml" -Encoding UTF8
@{Task=(Get-ScheduledTask -TaskName 'Wan22-ComfyUI' | Select-Object TaskName,State,Principal,Triggers);Firewall=(Get-NetFirewallRule -Name 'Wan22-ComfyUI-LAN-8188' | Select-Object Name,Enabled,Direction,Action)} | ConvertTo-Json -Depth 7 | Set-Content "$base\logs\service_configuration.json" -Encoding UTF8
foreach($n in @('Wan22-Bootstrap','Wan22-Acceleration','Wan22-Download-Models','Wan22-GPU-Monitor')){$t=Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue;if($t -and $t.State -ne 'Running'){Unregister-ScheduledTask -TaskName $n -Confirm:$false}}
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
