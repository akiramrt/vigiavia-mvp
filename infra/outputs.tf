output "url_mvp" {
  description = "URL pública (HTTPS) do MVP"
  value       = "https://${azurerm_container_app.app.ingress[0].fqdn}"
}

output "fqdn" {
  value = azurerm_container_app.app.ingress[0].fqdn
}

output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "container_app" {
  value = azurerm_container_app.app.name
}

output "acr_nome" {
  value = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

# Valores para os GitHub Secrets do workflow (identificadores, não senhas)
output "github_azure_client_id" {
  value = azurerm_user_assigned_identity.github.client_id
}

output "github_azure_tenant_id" {
  value = data.azurerm_client_config.atual.tenant_id
}

output "github_azure_subscription_id" {
  value = var.subscription_id
}
