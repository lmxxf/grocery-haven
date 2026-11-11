$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$base='C:\AI\Wan22-ComfyUI';$comfy="$base\ComfyUI_windows_portable\ComfyUI"
$aria=(Get-ChildItem "$base\tools\aria2" -Filter aria2c.exe -Recurse | Select-Object -First 1).FullName
$files=Get-Content "$base\scripts\model_manifest.json" -Raw | ConvertFrom-Json
$active=@();$pending=[Collections.Generic.Queue[object]]::new();foreach($f in $files){$pending.Enqueue($f)}
$results=@();$start=Get-Date;$tries=@{};$retries=@()
try {
 while($pending.Count -gt 0 -or $active.Count -gt 0){
  while($pending.Count -gt 0 -and $active.Count -lt 4){
   $f=$pending.Dequeue();if(-not $tries.ContainsKey($f.path)){$tries[$f.path]=0};$tries[$f.path]++;$parts=$f.path -split '/';$dir="$comfy\models\$($parts[1])";$name=$parts[-1];New-Item -ItemType Directory -Force -Path $dir | Out-Null
   $final="$dir\$name"
   if((Test-Path $final) -and (Get-Item $final).Length -eq $f.size){$results+=@{file=$name;state='existing';bytes=$f.size};continue}
   $url="https://huggingface.co/$($f.repository)/resolve/$($f.revision)/$($f.path)?download=true&cache_bust=$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
   $args=@('--all-proxy=http://192.168.31.198:17891','--continue=true','--auto-save-interval=5','--auto-file-renaming=false','--max-connection-per-server=8','--split=8','--min-split-size=16M','--file-allocation=none','--max-tries=20','--retry-wait=5','--connect-timeout=30','--timeout=120','--check-integrity=false','--console-log-level=warn','--summary-interval=30',"--dir=$dir","--out=$name.part",$url)
   $p=Start-Process -FilePath $aria -ArgumentList $args -RedirectStandardOutput "$base\logs\$name.download.out.log" -RedirectStandardError "$base\logs\$name.download.err.log" -PassThru -WindowStyle Hidden
   $null=$p.Handle;$active+=@{process=$p;file=$f;path=$final;part="$final.part";started=(Get-Date)}
   Write-Output "START $name pid=$($p.Id)"
  }
  $next=@()
  foreach($j in $active){
   if($j.process.HasExited){
    $j.process.WaitForExit();if($j.process.ExitCode -ne 0){
     $event=@{file=$j.file.path;code=$j.process.ExitCode;attempt=$tries[$j.file.path];time=(Get-Date).ToString('o')};$retries+=$event
     if($tries[$j.file.path] -ge 12){throw "Repeated download failure $($j.file.path)"}
     Get-Content "$base\logs\$([IO.Path]::GetFileName($j.file.path)).download.out.log" -Tail 12 | Add-Content "$base\logs\download_retries.log"
     if($j.process.ExitCode -eq 32){Remove-Item $j.part,"$($j.part).aria2" -ErrorAction SilentlyContinue}
     $pending.Enqueue($j.file);Write-Output "RETRY $($j.file.path) code=$($j.process.ExitCode)";continue
    }
    if((Get-Item $j.part).Length -ne $j.file.size){throw 'Model size mismatch'}
    $py="$base\ComfyUI_windows_portable\python_embeded\python.exe"
    if(Test-Path $py){
     $report=& $py -s "$base\scripts\verify_sha256.py" $j.part $j.file.sha256
     if($LASTEXITCODE -ne 0){throw 'Model SHA256 mismatch'}
     $hashInfo=$report | ConvertFrom-Json;$hash=$hashInfo.sha256
    }else{$hash=(Get-FileHash $j.part -Algorithm SHA256).Hash.ToLower();if($hash -ne $j.file.sha256){throw 'Model SHA256 mismatch'}}
    Move-Item $j.part $j.path -Force
    $item=@{file=$j.file.path;sha256=$hash;bytes=$j.file.size;seconds=((Get-Date)-$j.started).TotalSeconds;state='verified'};$results+=$item;Write-Output "VERIFIED $($j.file.path)"
   } else {$next+=$j}
  }
  $active=$next
  @{state='running';verified=$results;retries=$retries;active=@($active | ForEach-Object {$_.file.path});pending=$pending.Count;time=(Get-Date).ToString('o')} | ConvertTo-Json -Depth 6 | Set-Content "$base\logs\model_download_status.json" -Encoding UTF8
  Start-Sleep -Seconds 2
 }
 @{state='complete';verified=$results;retries=$retries;seconds=((Get-Date)-$start).TotalSeconds} | ConvertTo-Json -Depth 6 | Set-Content "$base\logs\model_download_status.json" -Encoding UTF8
} catch {
 @{state='failed';error=$_.Exception.Message;verified=$results} | ConvertTo-Json -Depth 6 | Set-Content "$base\logs\model_download_status.json" -Encoding UTF8
 foreach($j in $active){if(-not $j.process.HasExited){Stop-Process -Id $j.process.Id -Force}}
 throw
}
