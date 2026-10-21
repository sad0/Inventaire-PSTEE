@echo off
rem Installs Inventaire PTEE (Party Stash inventory page preview) on "PTEE (EEex release test)" from the repo.
rem Order matters: uninstall first (WeiDU restores old files), then copy the new mod files, then install.
set "REPO=E:\Enhanced Edition\Inventaire-PTEE\mod"
set "GAME=E:\Enhanced Edition\Environnement de test\PTEE (EEex release test)"
tasklist /fi "imagename eq Torment.exe" | find /i "Torment.exe" >nul
if not errorlevel 1 goto running
pushd "%GAME%"
if exist setup-InventairePTEE.exe .\setup-InventairePTEE.exe InventairePTEE/InventairePTEE.tp2 --uninstall --no-exit-pause --noautoupdate --log setup-InventairePTEE-uninstall.debug
popd
robocopy "%REPO%\InventairePTEE" "%GAME%\InventairePTEE" /MIR /NFL /NDL /NJH /NJS /NP >nul
copy /y "%REPO%\setup-InventairePTEE.exe" "%GAME%\setup-InventairePTEE.exe" >nul
pushd "%GAME%"
.\setup-InventairePTEE.exe InventairePTEE/InventairePTEE.tp2 --force-install 0 --language 0 --no-exit-pause --noautoupdate --log setup-InventairePTEE.debug
popd
if "%~1"=="" pause
exit /b 0
:running
echo Close the game first.
pause
exit /b 1
