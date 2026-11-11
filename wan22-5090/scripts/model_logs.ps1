$base='C:\AI\Wan22-ComfyUI'
Get-ChildItem "$base\logs\*.download.*.log" | ForEach-Object {Write-Output $_.Name;Get-Content $_.FullName -Tail 9}
