@echo off
rem Installs Inventaire PSTEE (Party Stash inventory page preview) on "PSTEE (EEex release test)" from the repo.
rem Order matters: uninstall first (WeiDU restores old files), then copy the new mod files, then install.
set "REPO=E:\Enhanced Edition\Inventaire-PSTEE\mod"
set "GAME=E:\Enhanced Edition\Environnement de test\PSTEE (EEex release test)"
tasklist /fi "imagename eq Torment.exe" | find /i "Torment.exe" >nul
if not errorlevel 1 goto running
pushd "%GAME%"
if exist setup-InventairePSTEE.exe .\setup-InventairePSTEE.exe InventairePSTEE/InventairePSTEE.tp2 --force-uninstall 0 --no-exit-pause --noautoupdate --log setup-InventairePSTEE-uninstall.debug
popd
robocopy "%REPO%\InventairePSTEE" "%GAME%\InventairePSTEE" /MIR /NFL /NDL /NJH /NJS /NP >nul
copy /y "%REPO%\setup-InventairePSTEE.exe" "%GAME%\setup-InventairePSTEE.exe" >nul
pushd "%GAME%"
.\setup-InventairePSTEE.exe InventairePSTEE/InventairePSTEE.tp2 --force-install 0 --language 0 --no-exit-pause --noautoupdate --log setup-InventairePSTEE.debug
popd
if "%~1"=="" pause
exit /b 0
:running
echo Close the game first.
pause
exit /b 1
