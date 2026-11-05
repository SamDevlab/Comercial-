# Gera config local para o Tunnel aprovado; NÃO cria DNS, Tunnel ou Access.
# Uso, após criar o Tunnel com o login Cloudflare autorizado:
# .\deploy\windows\generate-v5-tunnel-config.ps1 -TunnelId <UUID> -CredentialsFile <caminho-do-UUID.json>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][guid]$TunnelId,
  [Parameter(Mandatory=$true)][string]$CredentialsFile
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($TunnelId -eq [guid]::Empty) { throw 'UUID de Tunnel inválido.' }
if (-not (Test-Path -LiteralPath $CredentialsFile -PathType Leaf)) {
    throw 'Arquivo de credenciais de Tunnel não encontrado.'
}
$resolved = (Resolve-Path -LiteralPath $CredentialsFile).Path
if ([IO.Path]::GetExtension($resolved).ToLowerInvariant() -ne '.json') {
    throw 'O arquivo de credenciais deve ser o JSON do Tunnel.'
}
$protectedDir = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'CentralComercial'
if (-not (Test-Path -LiteralPath (Join-Path $protectedDir 'central-comercial.env') -PathType Leaf)) {
    throw 'Ambiente local ainda não inicializado; executar initialize-local.ps1 primeiro.'
}
$destination = Join-Path $protectedDir 'cloudflare-v5.yml'
if (Test-Path -LiteralPath $destination) {
    throw 'Configuração existente preservada. Não sobrescrever sem revisão.'
}
$yamlCredentials = ($resolved.Replace('\', '/') | ConvertTo-Json -Compress)
$content = @"
# Configuração privada gerada localmente. Access deve ser validado antes de publicar DNS.
tunnel: $($TunnelId.ToString())
credentials-file: $yamlCredentials
ingress:
  - hostname: central-comercial.wstecnologiaaplicada.com.br
    service: http://127.0.0.1:8765
    originRequest:
      httpHostHeader: central-comercial.wstecnologiaaplicada.com.br
      disableChunkedEncoding: true
  - service: http_status:404
"@
[IO.File]::WriteAllText($destination, $content, (New-Object System.Text.UTF8Encoding $false))
Write-Host "Configuração do Tunnel criada no diretório privado: $destination"
Write-Host 'Atenção: ainda NÃO foram criados Access, DNS ou Tunnel por este script.'
Write-Host 'Confira no Cloudflare a política Allow EXATA antes de criar a rota DNS.'
Write-Host 'Depois configure CENTRAL_PUBLIC_ORIGIN no ambiente protegido e valide:'
Write-Host 'cloudflared tunnel --config <caminho-privado> ingress validate'
