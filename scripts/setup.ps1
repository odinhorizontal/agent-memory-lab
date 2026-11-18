param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    exit $LASTEXITCODE
} finally { Pop-Location }
