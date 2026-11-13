param([int]$Seconds=60,[string]$Pattern='orbit',[int]$Delta=0)
$ErrorActionPreference='Stop'
Add-Type @'
using System;using System.Runtime.InteropServices;
public class MotionInput {
 [DllImport("user32.dll")]static extern void mouse_event(uint f,uint x,uint y,uint data,UIntPtr extra);
 [DllImport("user32.dll")]static extern void keybd_event(byte key,byte scan,uint f,UIntPtr extra);
 [DllImport("user32.dll")]static extern uint MapVirtualKey(uint key,uint type);
 [DllImport("user32.dll")]static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")]static extern uint GetWindowThreadProcessId(IntPtr h,out uint id);
 public static uint Foreground(){uint id;GetWindowThreadProcessId(GetForegroundWindow(),out id);return id;}
 public static void Move(int x,int y){mouse_event(1,unchecked((uint)x),unchecked((uint)y),0,UIntPtr.Zero);}
 public static void Key(byte key,bool down){keybd_event(key,(byte)MapVirtualKey(key,0),down?0u:2u,UIntPtr.Zero);}
}
'@
$p=Get-Process PBZ|Sort-Object WorkingSet64 -Descending|Select-Object -First 1
$stop='C:\Temp\egpu_probe\motion_stop'
Remove-Item $stop -ErrorAction SilentlyContinue
$clock=[Diagnostics.Stopwatch]::StartNew()
try{
 if($Pattern -eq 'turn'){for($i=0;$i -lt 20;$i++){if([MotionInput]::Foreground() -ne $p.Id){throw 'PBZ lost foreground'};[MotionInput]::Move([int]($Delta/20),0);Start-Sleep -Milliseconds 50}}
 elseif($Pattern -in @('forward','backward')){$key=if($Pattern -eq 'forward'){0x57}else{0x53};[MotionInput]::Key([byte]$key,$true);while($clock.Elapsed.TotalSeconds -lt $Seconds){if(Test-Path $stop){break};if([MotionInput]::Foreground() -ne $p.Id){break};Start-Sleep -Milliseconds 100}}
 else{while($clock.Elapsed.TotalSeconds -lt $Seconds){if(Test-Path $stop){break};if([MotionInput]::Foreground() -ne $p.Id){throw 'PBZ lost foreground'};[MotionInput]::Move(8,0);if($Pattern -eq 'walk'){[MotionInput]::Key(0x57,([int]($clock.Elapsed.TotalSeconds)%8 -lt 2));[MotionInput]::Key(0x53,([int]($clock.Elapsed.TotalSeconds)%8 -ge 4 -and [int]($clock.Elapsed.TotalSeconds)%8 -lt 6))};Start-Sleep -Milliseconds 100}}
}finally{foreach($k in @(0x57,0x53,0x41,0x44,0x10)){[MotionInput]::Key([byte]$k,$false)};"motion_finished pattern=$Pattern elapsed=$($clock.Elapsed.TotalSeconds)"|Set-Content 'C:\Temp\egpu_probe\motion_status.txt'}
