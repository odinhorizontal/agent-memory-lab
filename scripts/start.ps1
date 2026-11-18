param([int]$Port = 8501)
$ErrorActionPreference = "Stop"
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    & .\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port $Port
    exit $LASTEXITCODE
} finally { Pop-Location }
