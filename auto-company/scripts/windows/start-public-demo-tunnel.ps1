$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\.env"
$python = "C:\Users\Liza\Desktop\AIProjects\ai-roadmap-practice\venv\Scripts\python.exe"
$toolDir = Join-Path $projectRoot "tools"
$cloudflared = Join-Path $toolDir "cloudflared.exe"
$serverScript = Join-Path $projectRoot "scripts\core\public_demo_server.py"
$logFile = Join-Path $projectRoot "logs\cloudflared-demo.log"
$errorLogFile = Join-Path $projectRoot "logs\cloudflared-demo-error.log"
$port = 8790

function Test-ListeningPort([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Set-EnvValue([string]$Path, [string]$Name, [string]$Value) {
    $lines = if (Test-Path $Path) { @(Get-Content -LiteralPath $Path) } else { @() }
    $pattern = "^\s*" + [regex]::Escape($Name) + "\s*="
    $updated = $false
    $result = foreach ($line in $lines) {
        if ($line -match $pattern) {
            $updated = $true
            "$Name=`"$Value`""
        } else {
            $line
        }
    }
    if (-not $updated) {
        $result += "$Name=`"$Value`""
    }
    Set-Content -LiteralPath $Path -Value $result -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $toolDir, (Split-Path -Parent $logFile) | Out-Null
if (-not (Test-Path $cloudflared)) {
    Invoke-WebRequest `
        -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" `
        -OutFile $cloudflared `
        -UseBasicParsing
}

if (-not (Test-ListeningPort $port)) {
    Start-Process -FilePath $python -ArgumentList @("-u", $serverScript, "--port", $port) `
        -WorkingDirectory $projectRoot -WindowStyle Hidden
    for ($attempt = 0; $attempt -lt 20 -and -not (Test-ListeningPort $port); $attempt++) {
        Start-Sleep -Milliseconds 500
    }
}
if (-not (Test-ListeningPort $port)) {
    throw "Public demo server did not start on port $port."
}

$existing = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
if (-not $existing) {
    Remove-Item -LiteralPath $logFile, $errorLogFile -Force -ErrorAction SilentlyContinue
    Start-Process -FilePath $cloudflared `
        -ArgumentList @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:$port") `
        -WorkingDirectory $projectRoot -RedirectStandardOutput $logFile -RedirectStandardError $errorLogFile `
        -WindowStyle Hidden
}

$publicUrl = $null
for ($attempt = 0; $attempt -lt 30 -and -not $publicUrl; $attempt++) {
    Start-Sleep -Seconds 1
    $logPaths = @($logFile, $errorLogFile) | Where-Object { Test-Path $_ }
    if ($logPaths) {
        $match = Select-String -Path $logPaths -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -Last 1
        if ($match) {
            $publicUrl = $match.Matches.Value
        }
    }
}
if (-not $publicUrl) {
    throw "Cloudflare Tunnel did not provide a public URL. See $logFile."
}

Set-EnvValue $envFile "PUBLIC_DASHBOARD_URL" $publicUrl
Stop-ScheduledTask -TaskName "AutoCompany-TelegramBot" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "AutoCompany-TelegramBot"
Write-Output "PUBLIC_DEMO_URL=$publicUrl"
