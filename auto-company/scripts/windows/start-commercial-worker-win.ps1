$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\venv\Scripts\python.exe"
$env:COMMERCIAL_ENV_FILE = "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\.env"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = (Join-Path $projectRoot "scripts\core")

& $python -u (Join-Path $projectRoot "scripts\core\worker_loop.py")
exit $LASTEXITCODE
