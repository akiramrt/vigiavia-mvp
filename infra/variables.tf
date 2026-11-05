variable "subscription_id" {
  description = "ID da assinatura Azure (vem do terraform.tfvars, que fica fora do git)"
  type        = string
}

variable "location" {
  description = "Região Azure. Brazil South mantém os dados no Brasil (LGPD)."
  type        = string
  default     = "brazilsouth"
}

variable "prefixo" {
  description = "Prefixo dos nomes dos recursos"
  type        = string
  default     = "vigiavia"
}

variable "github_repo" {
  description = "Repositório autorizado a publicar via OIDC (dono/nome)"
  type        = string
  default     = "akiramrt/vigiavia-mvp"
}

variable "metrics_token" {
  description = "Token Bearer exigido pelo /metrics (guardado como segredo do Container App)"
  type        = string
  sensitive   = true
}

variable "tag_imagem" {
  description = "Tag da imagem no ACR usada na criação; depois o pipeline atualiza a imagem a cada deploy"
  type        = string
  default     = "inicial"
}

variable "tags" {
  description = "Tags aplicadas a todos os recursos (governança e custo)"
  type        = map(string)
  default = {
    projeto    = "VigiaVia"
    disciplina = "Secure DevOps Tools & Cloud Computing"
    ambiente   = "producao"
    gerenciado = "terraform"
  }
}
