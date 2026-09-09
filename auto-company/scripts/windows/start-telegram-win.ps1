$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\venv\Scripts\python.exe"
$env:GEMINI_PYTHON_BIN = $python
$env:AI_AGENT_SCRIPT = (Join-Path $projectRoot "scripts\core\provider-agent.py")
$env:TELEGRAM_ENV_FILE = "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\.env"
$env:AI_PROVIDER = "ollama"
$env:OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
$env:OLLAMA_MODEL = "qwen3:4b"
$env:OLLAMA_SMART_MODEL = "qwen3:8b"
$env:OLLAMA_NUM_PREDICT = "192"
$env:OLLAMA_NUM_CTX = "4096"
$env:OLLAMA_TEMPERATURE = "0.2"
$env:OLLAMA_ENABLE_TOOLS = "1"
$env:AI_REQUEST_TIMEOUT = "300"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:GEMINI_PROJECT_DIR = $projectRoot

& $python (Join-Path $projectRoot "scripts\core\telegram_bot.py")
exit $LASTEXITCODE
