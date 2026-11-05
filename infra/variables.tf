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

variable "github_oidc_subject" {
  description = <<-EOT
    Claim 'sub' do token OIDC do GitHub aceito pelo Azure (só a branch main). O GitHub usa IDs imutáveis
    do dono e do repositório (repo:<dono>@<id>/<repo>@<id>:ref:...), o que impede que um repositório
    recriado com o mesmo nome herde o acesso à nuvem.
  EOT
  type        = string
  default     = "repo:akiramrt@128194173/vigiavia-mvp@1446365122:ref:refs/heads/main"
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
