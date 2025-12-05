param(
    [string]$Entry = 'gui.py'
)

Write-Host "Starting PyInstaller one-dir (folder) build for $Entry"

# Ensure PyInstaller is available
$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "PyInstaller not found. Installing..."
    python -m pip install --user pyinstaller
}

# Exclude `info` module from bundling so that editable `info.py` in resource/ can be used at runtime.
# Include the entire `resource` folder as data so it will be copied to the dist folder.
$addData = "--add-data `"resource;resource`""
$exclude = "--exclude-module info"
$common = @('--noconfirm','--clean')

$cmd = @('pyinstaller') + $common + @($exclude, $addData, $Entry)

Write-Host ($cmd -join ' ')

$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = 'pyinstaller'
$processInfo.Arguments = ($common + @($exclude, $addData, $Entry)) -join ' '
$processInfo.UseShellExecute = $true

$proc = [System.Diagnostics.Process]::Start($processInfo)
$proc.WaitForExit()
if ($proc.ExitCode -eq 0) {
    Write-Host "One-dir build completed. Output in dist\$([System.IO.Path]::GetFileNameWithoutExtension($Entry))"
} else {
    Write-Host "Build failed with exit code $($proc.ExitCode)"
}
