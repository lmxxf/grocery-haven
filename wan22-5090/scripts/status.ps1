$base='C:\AI\Wan22-ComfyUI'
foreach($name in @('bootstrap_status.json','model_download_status.json','torch_inventory.json')){if(Test-Path "$base\logs\$name"){Write-Output $name;Get-Content "$base\logs\$name" -Raw}}
if(Test-Path "$base\logs\bootstrap.log"){Get-Content "$base\logs\bootstrap.log" -Tail 4}
Get-ChildItem "$base\ComfyUI_windows_portable\ComfyUI\models" -Filter '*.part' -Recurse -ErrorAction SilentlyContinue | Select-Object Name,Length | ConvertTo-Json
