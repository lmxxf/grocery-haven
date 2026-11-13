param([string]$Label,[string]$Mark)
$dir="C:\Temp\egpu_probe\phase4\$Label"
New-Item -ItemType Directory -Force $dir|Out-Null
@{mark=$Mark;utc=[DateTime]::UtcNow.ToString('o');qpc=[Diagnostics.Stopwatch]::GetTimestamp()}|ConvertTo-Json -Compress|Add-Content -Encoding UTF8 "$dir\marks.jsonl"
