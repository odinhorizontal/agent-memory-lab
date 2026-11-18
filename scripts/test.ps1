$ErrorActionPreference = "Stop"
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    & .\.venv\Scripts\python.exe -m pytest @args
    exit $LASTEXITCODE
} finally { Pop-Location }
