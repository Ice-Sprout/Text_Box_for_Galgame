# build_onefile_fixed.ps1 - Fixed version of build_onefile with icon handling and no markdown fences.
# Usage: run in repository root: .\build_onefile_fixed.ps1

param(
    [string]$Entry = 'gui.py'
)

Write-Host "Starting PyInstaller onefile build for $Entry"

# Ensure PyInstaller is available
$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "PyInstaller not found. Installing..."
    python -m pip install --user pyinstaller
}

Write-Host "Installing project requirements..."
python -m pip install --upgrade pip
if (Test-Path 'requirements.txt') { python -m pip install -r requirements.txt }

# Clean old build artifacts
if (Test-Path "build") { Remove-Item -Recurse -Force build }
if (Test-Path "dist") { Remove-Item -Recurse -Force dist }
if (Test-Path "release") { Remove-Item -Recurse -Force release }

# PyInstaller options
$pyArgs = @(
    '--noconfirm',
    '--clean',
    '--onefile',
    '--windowed',
    "--name=Text_Box_for_Hoshishiro",
    # Ensure info.py is bundled (some dynamic imports may be missed); include as hidden-import
    '--hidden-import=info'
)

# Icon handling: prefer resource/logo.ico; if only logo.png exists, try to convert to .ico using Pillow
$iconPng = Join-Path (Get-Location) "resource\logo.png"
$iconIco = Join-Path (Get-Location) "resource\logo.ico"
if (Test-Path $iconIco) {
    Write-Host "Using icon: $iconIco"
    $pyArgs += "--icon=$iconIco"
} elseif (Test-Path $iconPng) {
    Write-Host "Found logo.png, attempting to generate logo.ico using Pillow..."
    $py = @'
from PIL import Image
import sys
try:
    im = Image.open(r"resource/logo.png").convert("RGBA")
    sizes = [(256,256),(48,48),(32,32),(16,16)]
    im.save(r"resource/logo.ico", sizes=sizes)
    print("resource/logo.ico generated")
except Exception as e:
    print("failed to generate logo.ico:", e, file=sys.stderr)
    sys.exit(2)
'@
    $py | python -
    if (Test-Path $iconIco) {
        Write-Host "Generated $iconIco"
        $pyArgs += "--icon=$iconIco"
    } else {
        Write-Host "Could not generate logo.ico; continuing without icon"
    }
} else {
    Write-Host "No logo.ico or logo.png found; continuing without icon"
}

Write-Host "Running: pyinstaller $($pyArgs -join ' ') $Entry"
pyinstaller @pyArgs $Entry

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed (exit code $LASTEXITCODE)"
    exit 1
}

# Create release dir and copy exe
New-Item -ItemType Directory -Path .\release -Force | Out-Null
$builtExe = Join-Path (Get-Location) "dist\Text_Box_for_Hoshishiro.exe"
if (-not (Test-Path $builtExe)) { Write-Error "Built exe not found: $builtExe"; exit 1 }
Copy-Item $builtExe -Destination .\release\Text_Box_for_Hoshishiro.exe -Force

# Copy resource (include info.py)
if (Test-Path "resource") {
    Write-Host "Copying resource -> release/resource (including info.py)"
    New-Item -ItemType Directory -Path .\release\resource -Force | Out-Null
    robocopy .\resource .\release\resource /E | Out-Null
}

if (Test-Path "character") { robocopy .\character .\release\character /E | Out-Null }
if (Test-Path "background") { robocopy .\background .\release\background /E | Out-Null }

if (Test-Path "README.md") { Copy-Item README.md -Destination .\release -Force }

Write-Host "Build complete. Release directory: $(Resolve-Path .\release)"
Write-Host "Note: this build bundles 'info.py' into the exe (and also copies resource\info.py into release for reference)."