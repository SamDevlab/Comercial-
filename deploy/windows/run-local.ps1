$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
$servePath = Join-Path $PSScriptRoot 'serve.py'
$localData = [Environment]::GetFolderPath('LocalApplicationData')
$envPath = Join-Path $localData 'CentralComercial\central-comercial.env'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the project .venv first and install requirements-windows.txt.'
}
if (-not (Test-Path -LiteralPath $envPath)) {
    throw 'Run initialize-local.ps1 once before starting the panel.'
}

$allowedKeys = @(
    'CENTRAL_ADMIN_PASSWORD_HASH', 'CENTRAL_SESSION_SECRET', 'CENTRAL_PUBLIC_ORIGIN',
    'CENTRAL_BIND', 'CENTRAL_PORT', 'CENTRAL_PDF_MAX_BYTES',
    'CENTRAL_TRUSTED_PROXY_HOPS', 'LARK_SMTP_USER', 'LARK_SMTP_APP_PASSWORD'
)
$seenKeys = @{}
foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
    $separator = $line.IndexOf('=')
    if ($separator -lt 1) { throw 'Invalid local environment file; expected KEY=VALUE.' }
    $key = $line.Substring(0, $separator).Trim()
    $value = $line.Substring($separator + 1)
    if ($key -notmatch '^[A-Z][A-Z0-9_]*$') { throw 'Invalid environment variable name.' }
    if ($key -notin $allowedKeys) { throw 'Unexpected setting in the protected local environment file.' }
    if ($seenKeys.ContainsKey($key)) { throw 'Duplicate setting in the protected local environment file.' }
    $seenKeys[$key] = $true
    [Environment]::SetEnvironmentVariable($key, $value, 'Process')
}

foreach ($required in @('CENTRAL_ADMIN_PASSWORD_HASH', 'CENTRAL_SESSION_SECRET', 'CENTRAL_PUBLIC_ORIGIN')) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($required, 'Process'))) {
        throw "Missing required setting $required in the protected local environment file."
    }
}

Push-Location $repoRoot
try {
    Write-Host 'Starting the local panel on 127.0.0.1. Press Ctrl+C to stop it.'
    & $pythonPath $servePath
    if ($LASTEXITCODE -ne 0) { throw 'The local Waitress process exited with an error.' }
} finally {
    Pop-Location
}
