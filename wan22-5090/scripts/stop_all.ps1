$ErrorActionPreference='SilentlyContinue'
$base='C:\AI\Wan22-ComfyUI'
if(Get-ScheduledTask -TaskName 'Wan22-ComfyUI' -ErrorAction SilentlyContinue){
    Stop-ScheduledTask -TaskName 'Wan22-ComfyUI'
    Unregister-ScheduledTask -TaskName 'Wan22-ComfyUI' -Confirm:$false
}
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.ExecutablePath -like "$base\*" -or $_.CommandLine -like "*Wan22-ComfyUI*" }
if($procs){
    foreach($p in $procs){
        Write-Output "Stopping ComfyUI python.exe (PID=$($p.ProcessId))..."
        Stop-Process -Id $p.ProcessId -Force
    }
    Write-Output "Done! ComfyUI stopped and all RAM/VRAM released."
} else {
    Write-Output "ComfyUI is not running (RAM/VRAM already clean)."
}
