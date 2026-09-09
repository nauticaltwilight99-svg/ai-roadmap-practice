param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$repoWin = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$serverScript = Join-Path $repoWin "dashboard\\server.py"
if (-not (Test-Path $serverScript)) {
    throw "Dashboard server script not found: $serverScript"
}

$pythonCandidates = @(
    "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\venv\Scripts\python.exe",
    (Join-Path $HOME "Desktop\AIProjects\ai-roadmap-practice\venv\Scripts\python.exe"),
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
)
$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if ($null -eq $candidate) { continue }
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
}

if (-not $pythonExe) {
    throw "python not found in PATH."
}

$env:GEMINI_PYTHON_BIN = $pythonExe
$env:GEMINI_ENV_FILE = "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\.env"
$env:GEMINI_PROJECT_DIR = $repoWin
$env:GEMINI_AGENT_WIN = (Join-Path $repoWin "scripts\core\gemini-agent.py")

$url = "http://$BindHost`:$Port"
Write-Host "Starting dashboard server: $url"
Write-Host "Press Ctrl+C in this window to stop."

if (-not $NoBrowser) {
    Start-Process $url | Out-Null
}

& $pythonExe $serverScript --host $BindHost --port $Port
exit $LASTEXITCODE
