# Stash engine test on "PSTEE (EEex release test)" (John 2026-10-22: script it, no keyboard driving).
#  1. game must be closed;  2. sets [Party Stash] Autotest=1 in Baldur.lua;  3. installs the mod;  4. launches the game.
#  Then John loads a save and opens the inventory once: M_PSCORE.lua runs PSC_AutoTest() (store slot 16, list, take back).
#  5. run again with -Read to print the PSC lines of EEex.log.
#  -Open: opens the inventory with the I key sent to the inactive game window (tools\send_keys_bg.ps1), waits, reads.
param([switch]$Read, [switch]$Open)
$ErrorActionPreference = 'Stop'
$game = "E:\Enhanced Edition\Environnement de test\PSTEE (EEex release test)"
$ini = "$env:USERPROFILE\Documents\Planescape Torment - Enhanced Edition\Baldur.lua"
if ($Open) {
  & "$PSScriptRoot\send_keys_bg.ps1" -Keys 0x49
  Start-Sleep 3
  Select-String -Path "$game\EEex.log" -Pattern 'PSC' | ForEach-Object { $_.Line }; exit
}
if ($Read) { Select-String -Path "$game\EEex.log" -Pattern 'PSC' | ForEach-Object { $_.Line }; exit }
if (Get-Process Torment -ErrorAction SilentlyContinue) { throw 'Close the game first.' }
$lines = Get-Content $ini | Where-Object { $_ -notmatch "'Party Stash','Autotest'" }
$lines += "SetPrivateProfileString('Party Stash','Autotest','1')"
Set-Content -Path $ini -Value $lines -Encoding ascii
cmd /c "`"E:\Enhanced Edition\Environnement de test\Installer Inventaire PSTEE.bat`" nopause" | Select-String 'INSTALLED|ERROR'
Start-Process -FilePath "$game\InfinityLoader.exe" -WorkingDirectory $game
'Game launched: load a save, open the inventory once, then run: tools\test_stash.ps1 -Read'
