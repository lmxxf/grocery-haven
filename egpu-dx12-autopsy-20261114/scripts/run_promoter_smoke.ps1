$ErrorActionPreference='Stop'
$dir='C:\Temp\egpu_probe'
Set-Location $dir
foreach ($case in @(@{mode=0;spoof=0},@{mode=1;spoof=0},@{mode=1;spoof=1})) {
 $mode=$case.mode; $spoof=$case.spoof; $name="promoter_mode${mode}_spoof${spoof}"
 @"
[booster]
enabled=1
mode=$mode
min_buffer_kb=4
max_buffer_mb=64
min_heap_kb=64
max_heap_mb=128
max_total_mb=8
spoof_heap_properties=$spoof
"@ | Set-Content -Encoding ascii egpu_booster.ini
 if (Test-Path egpu_booster.log) {Remove-Item egpu_booster.log}
 $p=Start-Process -FilePath "$dir\promoter_smoke.exe" -ArgumentList "$mode $spoof" -WorkingDirectory $dir -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$dir\${name}.txt" -RedirectStandardError "$dir\${name}_stderr.txt"
 if(Test-Path egpu_booster.log){Copy-Item egpu_booster.log "${name}.log" -Force}
 Write-Output "$name exit_code=$($p.ExitCode)"
 if($p.ExitCode -ne 0){Get-Content "${name}.txt";exit $p.ExitCode}
}
