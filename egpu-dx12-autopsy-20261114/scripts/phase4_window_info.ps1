Add-Type @'
using System;using System.Text;using System.Runtime.InteropServices;
public class InspectWindows {
 [DllImport("user32.dll",CharSet=CharSet.Unicode)]static extern int GetClassName(IntPtr h,StringBuilder s,int n);
 [DllImport("user32.dll")]static extern bool IsWindowVisible(IntPtr h);
 public static string Class(IntPtr h){var s=new StringBuilder(256);GetClassName(h,s,256);return s.ToString();}
 public static bool Visible(IntPtr h){return IsWindowVisible(h);}
}
'@
$p=Get-Process b1-Win64-Shipping -ErrorAction Stop
[DesktopNative]::EnumWindows([DesktopNative+EnumProc]{param($h,$unused) $pid2=[uint32]0;[DesktopNative]::GetWindowThreadProcessId($h,[ref]$pid2)|Out-Null;if($pid2 -eq $p.Id){$r=New-Object DesktopNative+Rect;[DesktopNative]::GetWindowRect($h,[ref]$r)|Out-Null;$s=New-Object Text.StringBuilder 1024;[DesktopNative]::GetWindowText($h,$s,1024)|Out-Null;"hwnd=$h class=$([InspectWindows]::Class($h)) visible=$([InspectWindows]::Visible($h)) title=$s rect=$($r.Left),$($r.Top),$($r.Right),$($r.Bottom)"|Add-Content 'C:\Temp\egpu_probe\wukong_windows.txt'};return $true},[IntPtr]::Zero)|Out-Null
'windows_listed'
