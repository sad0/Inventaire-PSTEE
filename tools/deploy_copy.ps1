# Install the mod from the repo on the disposable test copy (Compat\PSTEE stash test) and re-add the test bridge.
$ErrorActionPreference = 'Continue'
$g = 'E:\Enhanced Edition\Environnement de test\Compat\PSTEE stash test'; $r = 'E:\Enhanced Edition\Inventaire-PSTEE'
Get-Process Torment,InfinityLoader -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$g*" } | Stop-Process -Force
Start-Sleep 2
Push-Location $g
.\setup-InventairePSTEE.exe InventairePSTEE/InventairePSTEE.tp2 --force-uninstall 0 --no-exit-pause --noautoupdate --log setup-u.debug 2>&1 | ForEach-Object { "$_" } | Select-String 'Uninstalled|ERROR'
robocopy "$r\mod\InventairePSTEE" "$g\InventairePSTEE" /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
.\setup-InventairePSTEE.exe InventairePSTEE/InventairePSTEE.tp2 --force-install 0 --language 0 --no-exit-pause --noautoupdate --log setup-i.debug 2>&1 | ForEach-Object { "$_" } | Select-String 'INSTALLED|ERROR|FATAL'
Pop-Location
& python "$r\tools\patch_copy_menu.py" "$g\override\UI.MENU"
Copy-Item "$r\tools\lua\M_ZBRDG.lua" "$g\override\" -Force
& python "$r\tools\bridge.py" reset
Set-Content -Path "$g\bridge\cmd_1.lua" -Encoding ascii -Value 'startEngine:OnContinueGame()'
Remove-Item "$g\InfinityLoader_Crash" -Recurse -Force -ErrorAction SilentlyContinue
Start-Process -FilePath "$g\InfinityLoader.exe" -WorkingDirectory $g
'copy relaunched'
