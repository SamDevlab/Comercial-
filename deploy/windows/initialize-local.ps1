$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the project .venv first and install requirements-windows.txt.'
}

$localData = [Environment]::GetFolderPath('LocalApplicationData')
$secretDirectory = Join-Path $localData 'CentralComercial'
if (Test-Path -LiteralPath $secretDirectory) {
    throw "Refusing to overwrite existing local data at $secretDirectory."
}

New-Item -ItemType Directory -Path $secretDirectory | Out-Null
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$accountGrant = '{0}:(OI)(CI)F' -f $account
$systemGrant = '*S-1-5-18:(OI)(CI)F'
$administratorsGrant = '*S-1-5-32-544:(OI)(CI)F'
& icacls.exe $secretDirectory /inheritance:r /grant:r $accountGrant $systemGrant $administratorsGrant | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'Could not restrict the local credential directory ACL.'
}

Push-Location $repoRoot
try {
    & $pythonPath (Join-Path $PSScriptRoot 'create_local_secrets.py') $secretDirectory
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create local credentials.'
    }
} finally {
    Pop-Location
}

Write-Host "Local secrets are stored under the current Windows user's protected LocalAppData: $secretDirectory"
Write-Host 'The generated admin password is in admin-password.txt. It was not printed.'
