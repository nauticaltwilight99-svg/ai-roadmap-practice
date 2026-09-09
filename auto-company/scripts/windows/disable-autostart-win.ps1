param(
    [string]$TaskName = "AutoCompany-WSL-Start"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command schtasks.exe -ErrorAction SilentlyContinue)) {
    throw "schtasks.exe not found."
}

& schtasks.exe /Query /TN $TaskName | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Autostart task not found: $TaskName"
    exit 0
}

$deleteOutput = & schtasks.exe /Delete /TN $TaskName /F 2>&1
if ($deleteOutput) {
    foreach ($line in $deleteOutput) {
        Write-Host $line
    }
}

if ($LASTEXITCODE -ne 0) {
    if (($deleteOutput -join "`n") -match "Access is denied") {
        throw "Failed to delete task due to permission error. Run PowerShell as Administrator and retry."
    }
    throw "Failed to delete scheduled task: $TaskName"
}

Write-Host "Autostart disabled: $TaskName"
