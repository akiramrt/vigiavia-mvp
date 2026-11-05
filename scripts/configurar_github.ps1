# Configura os GitHub Secrets e Variables do pipeline a partir dos outputs do Terraform.
# Todos os valores são IDENTIFICADORES (OIDC): não existe senha de nuvem a guardar.
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

$app = if ($o.container_app) { $o.container_app.value } else { 'ca-vigiavia-prod' }
$segredos = [ordered]@{
  AZURE_CLIENT_ID       = $o.github_azure_client_id.value
  AZURE_TENANT_ID       = $o.github_azure_tenant_id.value
  AZURE_SUBSCRIPTION_ID = $o.github_azure_subscription_id.value
  ACR_NOME              = $o.acr_nome.value
  ACA_NOME              = $app
  AZURE_RG              = $o.resource_group.value
}
foreach ($k in $segredos.Keys) {
  if (-not $segredos[$k]) { throw "Output ausente para $k — rode o terraform apply antes." }
  & $Gh secret set $k -R $Repo --body $segredos[$k]
  Write-Host "secret $k cadastrado"
}
& $Gh variable set PUBLICAR_IMAGEM -R $Repo --body true
Write-Host 'variable PUBLICAR_IMAGEM=true'
if ($HabilitarDeploy) {
  & $Gh variable set DEPLOY_HABILITADO -R $Repo --body true
  Write-Host 'variable DEPLOY_HABILITADO=true'
}
