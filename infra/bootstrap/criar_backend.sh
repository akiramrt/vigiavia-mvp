#!/usr/bin/env bash
# Cria (uma única vez) o Storage do state remoto do Terraform e gera infra/backend.hcl (ignorado pelo git).
# State fora do repositório, com versionamento de blobs, TLS 1.2, sem acesso público e SEM chave de conta:
# só identidades Entra ID com o papel "Storage Blob Data Contributor" leem/escrevem o state.
# Uso: bash infra/bootstrap/criar_backend.sh [regiao]
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash (Windows): não converter "/subscriptions/..." em caminho de arquivo
REGIAO="${1:-brazilsouth}"
RG="rg-vigiavia-tfstate"
# SA pode ser informado para reaproveitar uma conta já criada; senão, nome novo (lê só 4 bytes: sem SIGPIPE)
SA="${SA:-sttfvigiavia$(od -An -N4 -tx4 /dev/urandom | tr -dc 'a-f0-9' | cut -c1-6)}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"

az group create -n "$RG" -l "$REGIAO" --tags projeto=VigiaVia finalidade=terraform-state -o none
az storage account create -n "$SA" -g "$RG" -l "$REGIAO" --sku Standard_LRS --kind StorageV2 \
  --min-tls-version TLS1_2 --allow-blob-public-access false --allow-shared-key-access false \
  --https-only true -o none
az storage account blob-service-properties update -n "$SA" -g "$RG" --enable-versioning true \
  --enable-delete-retention true --delete-retention-days 14 -o none
EU="$(az ad signed-in-user show --query id -o tsv)"
ESCOPO="$(az storage account show -n "$SA" -g "$RG" --query id -o tsv)"
az role assignment create --assignee-object-id "$EU" --assignee-principal-type User \
  --role "Storage Blob Data Contributor" --scope "$ESCOPO" -o none
for i in $(seq 1 12); do   # a atribuição de papel leva alguns segundos para propagar
  az storage container create --account-name "$SA" -n tfstate --auth-mode login -o none 2>/dev/null && break
  sleep 10
done
cat > "$DIR/backend.hcl" <<EOF
resource_group_name  = "$RG"
storage_account_name = "$SA"
container_name       = "tfstate"
key                  = "vigiavia-prod.tfstate"
use_azuread_auth     = true
EOF
echo "State remoto pronto: $SA/tfstate -> $DIR/backend.hcl"
