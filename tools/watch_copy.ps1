# Test copy guard: when the disposable copy shows a crash dialog, kill it (so nothing lands on John's screen) and exit.
$g = 'E:\Enhanced Edition\Environnement de test\Compat\PSTEE stash test'
while ($true) {
  $p = Get-Process Torment -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$g*" }
  foreach ($x in $p) {
    if ($x.MainWindowTitle -match 'InfinityLoader|Lua|Error|Erreur') {
      "CRASH DIALOG: $($x.MainWindowTitle)"
      Get-Process Torment,InfinityLoader -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$g*" } | Stop-Process -Force
      exit 0
    }
  }
  Start-Sleep -Milliseconds 500
}
