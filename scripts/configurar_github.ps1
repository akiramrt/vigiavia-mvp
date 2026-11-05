# Configura os GitHub Secrets e Variables do pipeline a partir dos outputs do Terraform.
# Todos os valores sao IDENTIFICADORES (OIDC): nao existe senha de nuvem a guardar.
# (Arquivo propositalmente em ASCII puro: o Windows PowerShell 5.1 le .ps1 sem BOM como ANSI.)
# Uso (PowerShell, com gh autenticado):
#   powershell -ExecutionPolicy Bypass -File scripts\configurar_github.ps1 -Terraform <caminho\terraform.exe>
param(
  [string]$Repo = 'akiramrt/vigiavia-mvp',
  [string]$Terraform = 'terraform',
  [string]$Gh = 'C:\Program Files\GitHub CLI\gh.exe',
  [switch]$HabilitarDeploy
)
$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot '..\infra')
try { $o = & $Terraform output -json | ConvertFrom-Json } finally { Pop-Location }

$app = 'ca-vigiavia-prod'
if ($o.container_app) { $app = $o.container_app.value }
# Tenant e assinatura: outputs do Terraform ou, antes do apply completo, a sessao atual do Azure CLI
$conta = & az account show -o json | ConvertFrom-Json
$tenant = $conta.tenantId
if ($o.github_azure_tenant_id) { $tenant = $o.github_azure_tenant_id.value }
$assinatura = $conta.id
if ($o.github_azure_subscription_id) { $assinatura = $o.github_azure_subscription_id.value }
$segredos = [ordered]@{
  AZURE_CLIENT_ID       = $o.github_azure_client_id.value
  AZURE_TENANT_ID       = $tenant
  AZURE_SUBSCRIPTION_ID = $assinatura
  ACR_NOME              = $o.acr_nome.value
  ACA_NOME              = $app
  AZURE_RG              = $o.resource_group.value
}
foreach ($k in $segredos.Keys) {
  if (-not $segredos[$k]) { throw ('Output ausente para ' + $k + ': rode o terraform apply antes.') }
  & $Gh secret set $k -R $Repo --body $segredos[$k]
  Write-Host ('secret ' + $k + ' cadastrado')
}
& $Gh variable set PUBLICAR_IMAGEM -R $Repo --body true
Write-Host 'variable PUBLICAR_IMAGEM=true'
if ($HabilitarDeploy) {
  & $Gh variable set DEPLOY_HABILITADO -R $Repo --body true
  Write-Host 'variable DEPLOY_HABILITADO=true'
}
