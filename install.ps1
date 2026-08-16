# Termark installer for Windows.
# Run in PowerShell:  powershell -ExecutionPolicy Bypass -File install.ps1

$Here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BinDir = Join-Path $env:LOCALAPPDATA "termark\bin"

# 1. Python check.
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Host "Termark needs Python. Install it from python.org, then run this again."
    exit 1
}

# 2. Put a launcher on PATH.
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$launcher = Join-Path $BinDir "termark.cmd"
"@echo off`r`n`"$($py.Source)`" `"$Here\termark.py`" %*" | Set-Content -Encoding ASCII $launcher
Write-Host "Installed launcher at $launcher"

# 3. Add the folder to the user PATH if it is not there yet.
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    Write-Host "Added $BinDir to your PATH. Open a new terminal for it to take effect."
}

# 4. Point the user at the shell hook.
Write-Host ""
Write-Host "To capture full pages, add the hook to your PowerShell profile:"
Write-Host "    Add-Content `$PROFILE '. `"$Here\shell\termark.ps1`"'"
Write-Host ""
Write-Host "Then open a new terminal and run:  termark welcome"
