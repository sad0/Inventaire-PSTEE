# Send keystrokes to the game window WITHOUT focusing it (John 2026-10-22: inputs to inactive windows only).
# Uses PostMessage(WM_KEYDOWN/WM_CHAR/WM_KEYUP) on Torment.exe's main window; nothing goes to the foreground window.
# Usage: tools\send_keys_bg.ps1 -Keys 0x49            (single virtual keys, e.g. I = inventory)
# Limits (tested 2026-10-22): plain keys work on the inactive window; Ctrl/Alt combos do NOT (the game reads the
# real modifier state), so the debug console (Ctrl+Space) cannot be opened this way. Typed letters hit hotkeys.
param([string[]]$Console = @(), [string[]]$Keys = @(), [string]$Process = 'Torment', [switch]$NoOpen)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices; using System.Threading;
public static class BgKeys {
  [DllImport("user32.dll")] static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] static extern uint MapVirtualKey(uint code, uint type);
  const uint KEYDOWN = 0x100, KEYUP = 0x101, CHAR = 0x102;
  static IntPtr L(uint vk, bool up) {
    uint sc = MapVirtualKey(vk, 0);
    uint v = 1 | (sc << 16);
    if (up) v |= 0xC0000000;
    return (IntPtr)(int)v;
  }
  public static void Down(IntPtr h, uint vk) { PostMessage(h, KEYDOWN, (IntPtr)vk, L(vk, false)); Thread.Sleep(40); }
  public static void Up(IntPtr h, uint vk) { PostMessage(h, KEYUP, (IntPtr)vk, L(vk, true)); Thread.Sleep(40); }
  public static void Key(IntPtr h, uint vk) { Down(h, vk); Up(h, vk); }
  public static void Text(IntPtr h, string s) {
    foreach (char c in s) { PostMessage(h, CHAR, (IntPtr)c, (IntPtr)1); Thread.Sleep(25); }
  }
}
'@
$p = Get-Process $Process -ErrorAction Stop | Select-Object -First 1
$h = $p.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { throw "No window for $Process" }
foreach ($k in $Keys) { [BgKeys]::Key($h, [uint32]$k); Start-Sleep -Milliseconds 500 }
if ($Keys.Count -gt 0) { "keys sent to $Process"; exit }
if (-not $NoOpen) {
  [BgKeys]::Down($h, 0x11); [BgKeys]::Key($h, 0x20); [BgKeys]::Up($h, 0x11)   # Ctrl+Space: debug console
  Start-Sleep -Milliseconds 600
}
foreach ($c in $Console) {
  [BgKeys]::Text($h, $c); Start-Sleep -Milliseconds 150
  [BgKeys]::Key($h, 0x0D); Start-Sleep -Milliseconds 700                         # Enter
}
"sent to $Process (pid $($p.Id), hwnd $h)"
