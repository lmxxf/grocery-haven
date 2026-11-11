Get-NetTCPConnection -LocalPort 8188 -ErrorAction SilentlyContinue | Select-Object LocalAddress,State,OwningProcess | ConvertTo-Json
curl.exe -sS --max-time 5 -o NUL -w 'LOCAL_HTTP %{http_code}\n' http://127.0.0.1:8188/system_stats
Get-NetFirewallRule -Name 'Wan22-ComfyUI-LAN-8188' | Select-Object Enabled,Direction,Action | ConvertTo-Json
$base='C:\AI\Wan22-ComfyUI'
if(Test-Path "$base\logs\comfy.pid"){$serverProcessId=[int](Get-Content "$base\logs\comfy.pid");Get-Process -Id $serverProcessId | Select-Object Id,CPU,WorkingSet64,StartTime | ConvertTo-Json}
