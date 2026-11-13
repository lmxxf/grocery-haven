[DesktopNative]::SetThreadDpiAwarenessContext([IntPtr](-4))|Out-Null
[DesktopNative]::mouse_event(0x8001,[uint32](1560*65535/3839),[uint32](1954*65535/2159),0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 300
[DesktopNative]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
[DesktopNative]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
