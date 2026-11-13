if(-not('ReleaseGameKeys' -as [type])){Add-Type @'
using System;using System.Runtime.InteropServices;
public class ReleaseGameKeys{[DllImport("user32.dll")]static extern void keybd_event(byte k,byte s,uint f,UIntPtr p);public static void All(){foreach(byte k in new byte[]{0x57,0x53,0x41,0x44,0x10,0x11,0x12})keybd_event(k,0,2,UIntPtr.Zero);}}
'@}
[ReleaseGameKeys]::All()
'keys_released'
