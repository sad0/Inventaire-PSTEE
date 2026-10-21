# Build design/inventory_ptee.xcf: extract assets (system Python + Pillow), then let GIMP 3 assemble the layers.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot\..").Path
$gimp = "$env:LOCALAPPDATA\Programs\GIMP 3\bin\gimp-console-3.2.exe"

python "$root\tools\build_assets.py"
if ($LASTEXITCODE -ne 0) { throw 'build_assets failed' }

$ErrorActionPreference = 'Continue'  # GIMP chats on stderr
$env:INVPTEE_ROOT = $root
# separate GIMP profile: a running GIMP (John's) must not block the batch
$env:GIMP3_DIRECTORY = Join-Path $env:TEMP 'invptee-gimp-profile'
$script = "$root\tools\gimp_build.py" -replace '\\', '/'
& $gimp -i --batch-interpreter=python-fu-eval -b "exec(open('$script', encoding='utf-8').read())" --quit
Copy-Item "$root\design\preview\inventory_ptee_preview.png" "$root\design\inventory_ptee_preview.png"
Get-Content "$root\design\build\gimp_build.log"
