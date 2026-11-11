$ErrorActionPreference='Stop';$base='C:\AI\Wan22-ComfyUI'
try {
 @{state='running';time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content "$base\logs\bootstrap_status.json" -Encoding UTF8
 & "$base\scripts\bootstrap.ps1" *>> "$base\logs\bootstrap.log"
 @{state='complete';time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content "$base\logs\bootstrap_status.json" -Encoding UTF8
} catch {
 $_ | Format-List * -Force | Out-File "$base\logs\bootstrap_error.log" -Append
 @{state='failed';error=$_.Exception.Message;time=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content "$base\logs\bootstrap_status.json" -Encoding UTF8
 exit 1
}
