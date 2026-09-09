$ErrorActionPreference = 'Stop'

$envPath = Join-Path $PSScriptRoot '..\..\..\ai-roadmap-practice\.env'
$envPath = [System.IO.Path]::GetFullPath($envPath)
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Missing .env file: $envPath"
}

Write-Host 'Enter the Telegram bot token. Characters will not be displayed.'
$secureToken = Read-Host 'TELEGRAM_BOT_TOKEN' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

if ([string]::IsNullOrWhiteSpace($token) -or $token -notmatch '^\d+:[A-Za-z0-9_-]+$') {
    throw 'The value does not look like a Telegram Bot Token.'
}

$lines = @(Get-Content -LiteralPath $envPath -ErrorAction Stop)
$updated = $false
$output = foreach ($line in $lines) {
    if ($line -match '^TELEGRAM_BOT_TOKEN=') {
        $updated = $true
        "TELEGRAM_BOT_TOKEN=$token"
    }
    else {
        $line
    }
}
if (-not $updated) {
    $output += "TELEGRAM_BOT_TOKEN=$token"
}
if (-not ($output -match '^TELEGRAM_OWNER_CHAT_ID=')) {
    $output += 'TELEGRAM_OWNER_CHAT_ID='
}
Set-Content -LiteralPath $envPath -Value $output -Encoding UTF8
Remove-Variable token -ErrorAction SilentlyContinue
Write-Host 'Token saved to .env. Run the validation command next.'
