for($i=0;$i -lt 6;$i++){
 Start-Sleep -Seconds 10
 "elapsed_s=$(($i+1)*10)"
 Get-Process PBZ -ErrorAction SilentlyContinue | Select-Object Id,CPU,WorkingSet64 | Format-Table -HideTableHeaders
 Get-Content 'D:\SteamLibrary\steamapps\common\PBZ\platform\steam\egpu_booster.log' -Tail 12 -ErrorAction SilentlyContinue | Where-Object {$_ -match '^(snapshot |heap_ledger |promotion mode=)'} | Select-Object -Last 3
}
