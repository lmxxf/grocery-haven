$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing,System.Windows.Forms
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class DesktopNative {
 [DllImport("kernel32.dll")]static extern uint GetCurrentThreadId();
 [DllImport("user32.dll")]static extern bool AttachThreadInput(uint a,uint b,bool attach);
 [DllImport("user32.dll")]static extern bool BringWindowToTop(IntPtr h);
 [DllImport("user32.dll")]static extern bool IsIconic(IntPtr h);
 public static bool Activate(IntPtr h){uint pid;uint fg=GetWindowThreadProcessId(GetForegroundWindow(),out pid),cur=GetCurrentThreadId();bool joined=fg!=cur&&AttachThreadInput(cur,fg,true);if(IsIconic(h))ShowWindow(h,9);else ShowWindow(h,5);BringWindowToTop(h);SetForegroundWindow(h);if(joined)AttachThreadInput(cur,fg,false);return GetForegroundWindow()==h;}

 public delegate bool EnumProc(IntPtr h,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb,IntPtr p);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint pid);
 [StructLayout(LayoutKind.Sequential)] public struct Rect {public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h,out Rect r);
 public static IntPtr FindMain(uint pid){IntPtr found=IntPtr.Zero;long max=-1;EnumWindows((h,p)=>{uint id;GetWindowThreadProcessId(h,out id);Rect r;if(id==pid && GetWindowRect(h,out r)){long area=(long)(r.Right-r.Left)*(r.Bottom-r.Top);var cls=new StringBuilder(128);GetClassName(h,cls,128);if(cls.ToString()=="UnrealWindow")area+=(1L<<50);if(area>max){max=area;found=h;}}return true;},IntPtr.Zero);return found;}

 [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr value);
 [DllImport("user32.dll")] public static extern int GetSystemMetrics(int index);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int mode);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint msg,IntPtr w,IntPtr l);
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint x,uint y,uint data,UIntPtr extra);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern bool EnumDisplaySettings(string name,int mode,IntPtr dm);
}
'@
$base='C:\Temp\egpu_probe'
"session=$((Get-Process -Id $PID).SessionId) pid=$PID" | Set-Content "$base\desktop_ready.txt"
while(-not(Test-Path "$base\desktop_stop")){
 if(Test-Path "$base\desktop_command.json"){
  try{
   $cmd=Get-Content "$base\desktop_command.json" -Raw | ConvertFrom-Json
   Remove-Item "$base\desktop_command.json"
   $out=& {
    switch($cmd.action){
     'script' {& $cmd.path}
     'launch_direct' {Start-Process $cmd.path -WorkingDirectory (Split-Path $cmd.path); 'direct_launch_requested'}
     'launch' {Start-Process 'C:\Program Files (x86)\Steam\steam.exe' -ArgumentList "-applaunch $($cmd.appid)"; 'launch_requested'}
     'focus' {$proc=Get-Process -Name $cmd.process -ErrorAction Stop|Select-Object -First 1;$wnd=[DesktopNative]::FindMain($proc.Id);if($wnd -eq [IntPtr]::Zero){throw 'No game window found'};if(-not([DesktopNative]::Activate($wnd))){throw 'Game foreground activation failed'};"focused hwnd=$wnd"}
     'key' {$proc=Get-Process -Name $cmd.process -ErrorAction Stop|Select-Object -First 1;$wnd=[DesktopNative]::FindMain($proc.Id);if($wnd -eq [IntPtr]::Zero){throw 'No game window found; no keys sent'};if(-not([DesktopNative]::Activate($wnd))){throw 'Game foreground activation failed'};Start-Sleep -Milliseconds 200;[Windows.Forms.SendKeys]::SendWait($cmd.keys);'keys_sent'}
     'click' {[DesktopNative]::SetThreadDpiAwarenessContext([IntPtr](-4))|Out-Null;$w=[DesktopNative]::GetSystemMetrics(78);$h=[DesktopNative]::GetSystemMetrics(79);[DesktopNative]::mouse_event(0x8001,[uint32]($cmd.x*65535/($w-1)),[uint32]($cmd.y*65535/($h-1)),0,[UIntPtr]::Zero);Start-Sleep -Milliseconds 150;[DesktopNative]::mouse_event(2,0,0,0,[UIntPtr]::Zero);[DesktopNative]::mouse_event(4,0,0,0,[UIntPtr]::Zero);'click_sent'}
     'close' {$proc=Get-Process -Name $cmd.process -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object -First 1;if($proc){[DesktopNative]::PostMessage($proc.MainWindowHandle,0x10,[IntPtr]::Zero,[IntPtr]::Zero)|Out-Null};'close_requested'}
     'screenshot' {
      [DesktopNative]::SetThreadDpiAwarenessContext([IntPtr](-4))|Out-Null
      $w=[DesktopNative]::GetSystemMetrics(78);$h=[DesktopNative]::GetSystemMetrics(79);$x=[DesktopNative]::GetSystemMetrics(76);$y=[DesktopNative]::GetSystemMetrics(77)
      $bmp=New-Object Drawing.Bitmap($w,$h);$g=[Drawing.Graphics]::FromImage($bmp);$g.CopyFromScreen($x,$y,0,0,(New-Object Drawing.Size($w,$h)));$bmp.Save("$base\desktop.png",[Drawing.Imaging.ImageFormat]::Png);$g.Dispose();$bmp.Dispose();'screenshot_saved'
     }
     'info' {$s=New-Object Text.StringBuilder 1024;[DesktopNative]::GetWindowText([DesktopNative]::GetForegroundWindow(),$s,1024)|Out-Null;"foreground=$s";[Windows.Forms.Screen]::AllScreens | ForEach-Object {"screen=$($_.DeviceName) bounds=$($_.Bounds) primary=$($_.Primary)"};$dm=[Runtime.InteropServices.Marshal]::AllocHGlobal(220);try{for($i=0;$i -lt 220;$i++){[Runtime.InteropServices.Marshal]::WriteByte($dm,$i,0)};[Runtime.InteropServices.Marshal]::WriteInt16($dm,68,220);if([DesktopNative]::EnumDisplaySettings($null,-1,$dm)){"display width=$([Runtime.InteropServices.Marshal]::ReadInt32($dm,172)) height=$([Runtime.InteropServices.Marshal]::ReadInt32($dm,176)) hz=$([Runtime.InteropServices.Marshal]::ReadInt32($dm,184))"}}finally{[Runtime.InteropServices.Marshal]::FreeHGlobal($dm)}}
    }
   }
   @{id=$cmd.id;ok=$true;output=($out|Out-String)}|ConvertTo-Json|Set-Content -Encoding UTF8 "$base\desktop_result.json"
  }catch{@{id=$cmd.id;ok=$false;error="$_"}|ConvertTo-Json|Set-Content -Encoding UTF8 "$base\desktop_result.json"}
 }
 Start-Sleep -Milliseconds 300
}
