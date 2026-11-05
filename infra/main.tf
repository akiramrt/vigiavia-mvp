# Infraestrutura de produção do VigiaVia (Azure). Tudo criado por código; nada "clicado" no portal.
#
#   Internet --HTTPS 443--> Container Apps (ingress gerenciado, TLS) --> container da API (porta 8000 interna)
#   GitHub Actions --OIDC (sem senha)--> Entra ID --> push no ACR + update do Container App
#
# Não existe porta administrativa (SSH/RDP): a plataforma é gerenciada e a operação é feita pelo plano de
# controle do Azure, autenticado e auditado. O único ingress é HTTPS, com HTTP inseguro desabilitado.

data "azurerm_client_config" "atual" {}

resource "random_string" "sufixo" {
  length  = 5
  upper   = false
  special = false
}

locals {
  nome = "${var.prefixo}-prod"
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.nome}"
  location = var.location
  tags     = var.tags
}

# Logs da plataforma (stdout/stderr dos containers e eventos do sistema)
resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${local.nome}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 1 # teto de custo
  tags                = var.tags
}

# Registro privado de imagens: sem usuário admin (só identidades com RBAC)
resource "azurerm_container_registry" "acr" {
  name                = "acr${var.prefixo}${random_string.sufixo.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "Basic"
  admin_enabled       = false
  tags                = var.tags
}

# Identidade do app para puxar a imagem do ACR (sem senha de registro)
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.nome}-app"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

resource "azurerm_role_assignment" "app_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-${local.nome}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  tags                       = var.tags

  # perfil serverless (paga por uso); o Azure cria ambientes novos já com ele
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

resource "azurerm_container_app" "app" {
  name                         = "ca-${local.nome}"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  # Segredo injetado em tempo de execução (nunca na imagem nem no repositório)
  secret {
    name  = "metrics-token"
    value = var.metrics_token
  }

  ingress {
    external_enabled           = true
    target_port                = 8000
    transport                  = "auto"
    allow_insecure_connections = false # somente HTTPS
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1 # sem "cold start" para o cidadão e para a banca
    max_replicas = 1 # 1 réplica no MVP: custo baixo e métricas consistentes (ver relatório)

    container {
      name   = "api"
      image  = "${azurerm_container_registry.acr.login_server}/vigiavia-mvp:${var.tag_imagem}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "METRICS_TOKEN"
        secret_name = "metrics-token"
      }
      env {
        name  = "VIGIAVIA_THREADS"
        value = "1"
      }
      env {
        name  = "VIGIAVIA_SEMEAR_DEMO"
        value = "true"
      }

      # No teste de carga (16 clientes, CPU no limite de 0,5 vCPU) o /health passou do timeout padrão de 1 s
      # e a liveness reiniciou o container. 5 s dá folga sem esconder um processo travado: o reinício só
      # acontece após 3 falhas seguidas (~90 s).
      liveness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        initial_delay           = 10
        interval_seconds        = 30
        timeout                 = 5
        failure_count_threshold = 3
      }
      # Com 1 réplica, uma readiness reprovada tira o app do balanceamento (503 no ingress): mesmo timeout.
      readiness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        interval_seconds        = 10
        timeout                 = 5
        failure_count_threshold = 3
      }
    }
  }

  lifecycle {
    # a imagem é trocada pelo pipeline a cada deploy; o Terraform não deve "voltar" a versão
    ignore_changes = [template[0].container[0].image]
  }

  depends_on = [azurerm_role_assignment.app_pull]
}

# ---------------------------------------------------------------- deploy pelo GitHub Actions (OIDC)
# Identidade federada: o GitHub troca um token OIDC de curta duração por acesso ao Azure.
# Nenhuma senha/chave de longa duração existe para vazar. Só a branch main do repositório pode usar.
resource "azurerm_user_assigned_identity" "github" {
  name                = "id-${local.nome}-github"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "github_main" {
  name                = "github-main"
  resource_group_name = azurerm_resource_group.rg.name
  parent_id           = azurerm_user_assigned_identity.github.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = var.github_oidc_subject
}

# Menor privilégio: push só neste ACR e escrita só neste grupo de recursos
resource "azurerm_role_assignment" "github_push" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPush"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_deploy" {
  scope                = azurerm_resource_group.rg.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}
