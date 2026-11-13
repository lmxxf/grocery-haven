param([string]$Label,[ValidateSet('wukong','pbz')][string]$Game='wukong',[int]$Seconds=120)
$ErrorActionPreference='Stop'
$dest="C:\Temp\egpu_probe\phase4\$Label"
New-Item -ItemType Directory -Force $dest | Out-Null
$gameDir=if($Game -eq 'wukong'){'D:\SteamLibrary\steamapps\common\BlackMythWukong\b1\Binaries\Win64'}else{'D:\SteamLibrary\steamapps\common\PBZ\platform\steam'}
$proc=if($Game -eq 'wukong'){'b1-Win64-Shipping'}else{'PBZ'}
$config=if($Game -eq 'wukong'){'C:\Users\seth\AppData\Local\b1\Saved\Config\Windows'}else{'C:\Users\seth\AppData\Local\ProjectPBZ\Saved\Config\Windows'}
$log="$gameDir\egpu_booster.log"
$startBytes=if(Test-Path $log){(Get-Item $log).Length}else{0}
Add-Type @'
using System;using System.Runtime.InteropServices;
public class ProbeThreadName {
 [DllImport("kernel32.dll")]static extern IntPtr OpenThread(uint flags,bool inherit,uint tid);
 [DllImport("kernel32.dll")]static extern int GetThreadDescription(IntPtr h,out IntPtr name);
 [DllImport("kernel32.dll")]static extern IntPtr LocalFree(IntPtr p);
 [DllImport("kernel32.dll")]static extern bool CloseHandle(IntPtr h);
 public static string Name(uint tid){IntPtr h=OpenThread(0x800,false,tid);if(h==IntPtr.Zero)return "";try{IntPtr p;if(GetThreadDescription(h,out p)!=0)return "";try{return Marshal.PtrToStringUni(p);}finally{LocalFree(p);}}finally{CloseHandle(h);}}
}
'@
function ThreadCpu($path){$process=Get-Process $proc -ErrorAction SilentlyContinue|Sort-Object WorkingSet64 -Descending|Select-Object -First 1;if($process){$process.Threads|ForEach-Object{try{[pscustomobject]@{tid=$_.Id;name=[ProbeThreadName]::Name($_.Id);cpu100ns=$_.TotalProcessorTime.Ticks;user100ns=$_.UserProcessorTime.Ticks;kernel100ns=$_.PrivilegedProcessorTime.Ticks;startUtc=$_.StartTime.ToUniversalTime().ToString('o')}}catch{}}|ConvertTo-Json|Set-Content -Encoding UTF8 $path}}
ThreadCpu "$dest\thread_cpu_start.json"
$start=[DateTime]::UtcNow.ToString('o');$startQpc=[Diagnostics.Stopwatch]::GetTimestamp()
Get-Process $proc -ErrorAction SilentlyContinue | Select-Object Name,Id,SessionId,StartTime,CPU,PriorityClass | ConvertTo-Json | Set-Content "$dest\process_start.json"
Copy-Item "$gameDir\egpu_booster.ini" "$dest\egpu_booster.ini"
Copy-Item "$config\GameUserSettings.ini" "$dest\GameUserSettings.ini" -ErrorAction SilentlyContinue
Copy-Item "$config\Engine.ini" "$dest\Engine.ini" -ErrorAction SilentlyContinue
Get-FileHash "$gameDir\dxgi.dll" | ConvertTo-Json | Set-Content "$dest\dll_hash.json"
& nvidia-smi -q | Set-Content "$dest\gpu_before.txt"
$query=Start-Process nvidia-smi -ArgumentList '--query-gpu=timestamp,pcie.link.gen.current,pcie.link.width.current,memory.used,utilization.gpu,utilization.memory,temperature.gpu,power.draw --format=csv -l 1' -NoNewWindow -PassThru -RedirectStandardOutput "$dest\gpu_query.csv" -RedirectStandardError "$dest\gpu_query_stderr.txt"
$count=0
try {& nvidia-smi dmon -s uct -d 1 -c $Seconds | ForEach-Object {$_ | Add-Content -Encoding ascii "$dest\dmon.txt";if($_ -match '^\s*\d'){ "$([DateTime]::UtcNow.ToString('o'))|$_" | Add-Content -Encoding ascii "$dest\dmon_timestamp.txt"; $count++;if($count%15 -eq 0){"sample=$count label=$Label"}}}}finally{if(-not $query.HasExited){Stop-Process -Id $query.Id -ErrorAction SilentlyContinue}}
ThreadCpu "$dest\thread_cpu_end.json"
$end=[DateTime]::UtcNow.ToString('o');$endQpc=[Diagnostics.Stopwatch]::GetTimestamp()
if(Test-Path $log){
 $f=[IO.File]::Open($log,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 try{$length=$f.Length;$bytes=New-Object byte[] $length;$pos=0;while($pos -lt $length){$n=$f.Read($bytes,$pos,$length-$pos);if($n -eq 0){break};$pos+=$n}}finally{$f.Dispose()}
 [IO.File]::WriteAllBytes("$dest\egpu_booster.full.log",$bytes)
 if($bytes.Length -gt $startBytes){[IO.File]::WriteAllBytes("$dest\egpu_booster.window.log",$bytes[$startBytes..($bytes.Length-1)])}
}
@{label=$Label;game=$Game;startUtc=$start;endUtc=$end;startQpc=$startQpc;endQpc=$endQpc;qpcFrequency=[Diagnostics.Stopwatch]::Frequency;secondsRequested=$Seconds;dmonSamples=$count;startLogBytes=$startBytes} | ConvertTo-Json | Set-Content "$dest\window.json"
Get-Process $proc -ErrorAction SilentlyContinue | Select-Object Name,Id,SessionId,StartTime,CPU,PriorityClass | ConvertTo-Json | Set-Content "$dest\process_end.json"
"collected=$Label"
