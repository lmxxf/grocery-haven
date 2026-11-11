$base='C:\AI\Wan22-ComfyUI';$p=Get-Process 7zr -ErrorAction SilentlyContinue
if($p){$p | Select-Object Id,CPU,WorkingSet64,StartTime | ConvertTo-Json}
Get-CimInstance Win32_Processor | Select-Object Name,LoadPercentage | ConvertTo-Json
Get-CimInstance Win32_PerfFormattedData_PerfDisk_PhysicalDisk | Select-Object Name,PercentDiskTime,DiskReadBytesPersec,DiskWriteBytesPersec,CurrentDiskQueueLength | ConvertTo-Json
$site="$base\ComfyUI_windows_portable\python_embeded\Lib\site-packages"
if(Test-Path $site){$dirs=@(Get-ChildItem $site -Directory);@{PackageDirs=$dirs.Count;LastPackageNames=@($dirs | Select-Object -Last 8 -ExpandProperty Name);PythonExists=(Test-Path "$base\ComfyUI_windows_portable\python_embeded\python.exe")} | ConvertTo-Json}
