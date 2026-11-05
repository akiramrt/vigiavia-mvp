terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.12"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }
  # State REMOTO no Azure Storage (fora do repositório), com autenticação Entra ID (sem chave de conta).
  # Os parâmetros vêm de backend.hcl, gerado por infra/bootstrap/criar_backend.sh e ignorado pelo git:
  #   terraform init -backend-config=backend.hcl
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}
