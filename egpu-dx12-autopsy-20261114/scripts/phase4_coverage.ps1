$log='D:\SteamLibrary\steamapps\common\BlackMythWukong\b1\Binaries\Win64\egpu_booster.log'
Get-Content $log -Tail 180 | Select-String 'coverage|cpu_breakdown|copy_detail|swapchain |snapshot '
