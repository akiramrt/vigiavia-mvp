# VigiaVia — MVP em produção (Secure DevOps & Cloud)

> **Deploy Blindado** · FIAP Global Solution 2026.2 · CitizenTech · Engenharia de Software 4º ano (4ES)
> Disciplina **Secure DevOps Tools & Cloud Computing** (Profs. Gabriel Arcanjo e Cleórbete Santos)

[![DevSecOps](https://github.com/akiramrt/vigiavia-mvp/actions/workflows/devsecops.yml/badge.svg)](https://github.com/akiramrt/vigiavia-mvp/actions/workflows/devsecops.yml)

**🌐 MVP no ar:** https://ca-vigiavia-prod.happywave-0bf5b4c3.brazilsouth.azurecontainerapps.io · 📄 [Relatório da disciplina (PDF)](docs/relatorio/VigiaVia_Secure_DevOps.pdf) ·
🧠 [Componente de visão computacional](https://github.com/akiramrt/vigiavia-visao-computacional)

| Integrante | RM |
|---|---|
| Deivison Pertel | 550803 |
| Eduardo Akira Murata | 98713 |
| Wesley Souza de Oliveira | 97874 |

## Ficha técnica do MVP

| Item | VigiaVia |
|---|---|
| **Nome do produto** | VigiaVia — zeladoria inteligente de vias públicas |
| **Cidadão e território** | Quem circula pelas vias (motociclistas, ciclistas, pedestres, motoristas, usuários de ônibus) e os agentes de zeladoria das subprefeituras. Piloto: centro de São Paulo (Bela Vista). |
| **Problema, em uma frase** | Buracos nas vias causam acidentes e custos, e sua identificação depende de chamados manuais, lentos, imprecisos e duplicados (113,1 mil pedidos de tapa-buraco em SP em 2025). |
| **Proposta de valor** | Detectar buracos automaticamente com as câmeras que já circulam pela cidade e entregar à zeladoria um relato único, georreferenciado e priorizado por buraco — com privacidade e validação humana. |
| **Arquitetura: componentes** | API FastAPI + interface web (cidadão e zeladoria) · detector YOLO26n em ONNX Runtime · fila de relatos com deduplicação geográfica · Azure Container Apps + ACR + Log Analytics (Terraform) · pipeline DevSecOps (GitHub Actions) · Prometheus + Grafana. |
| **Fontes de dados** | RDD2022 (treino do modelo, CC BY-SA 4.0); relatos e detecções enviados pelos cidadãos; dados de demonstração simulados na Bela Vista (sinalizados como `demonstracao`). |
| **Modelos de IA utilizados** | YOLO26n treinado no RDD2022 (mAP@0,5 = 0,585 no teste), exportado para ONNX; executado no servidor (ONNX Runtime) ou no navegador (onnxruntime-web). |
| **URL do MVP e repositório** | https://ca-vigiavia-prod.happywave-0bf5b4c3.brazilsouth.azurecontainerapps.io · https://github.com/akiramrt/vigiavia-mvp |
| **Indicadores de impacto** | Tempo entre detecção e reparo · % de chamados duplicados evitados · buracos detectados por km rodado · precisão das detecções confirmadas pela zeladoria. Operação: disponibilidade, p95 de latência, taxa de erros e saturação (4 sinais de ouro). |
| **ODS conectados** | **11.2** transporte seguro (reparo mais rápido e alerta ao condutor reduzem quedas de motos e bicicletas) · **11.3** gestão participativa (o cidadão relata e confirma; a fila prioriza o que a população aponta) · **9.1** infraestrutura resiliente (reparo antes de o buraco crescer) · **3.6** menos lesões e mortes no trânsito. Cada meta é acompanhada pelos indicadores acima. |

## Arquitetura

![Arquitetura de produção](docs/img/arquitetura.png)

| Camada | Como foi feito | Por quê |
|---|---|---|
| **Container** | [`Dockerfile`](Dockerfile) multi-stage, `python:3.12-slim`, usuário 10001, `HEALTHCHECK`, sem PyTorch | imagem pequena = menos vulnerabilidades e deploy rápido; nenhum segredo na imagem |
| **Stack local** | [`docker-compose.yml`](docker-compose.yml): API (read-only, `cap_drop: ALL`, `no-new-privileges`) + Prometheus + Grafana (presos a `127.0.0.1`) | mesma stack para desenvolver e para observar; validada a cada push no pipeline |
| **Nuvem (IaC)** | [`infra/`](infra) — Terraform: RG, Log Analytics, ACR, identidades gerenciadas, RBAC, Container Apps, OIDC | nada criado à mão; state remoto no Azure Storage (Entra ID, sem chave); `.tfvars` e `backend.hcl` fora do git |
| **Rede** | ingress gerenciado **somente HTTPS**; **nenhuma porta administrativa** (SSH/RDP) existe | não há porta admin para abrir a `0.0.0.0/0` — a operação é feita pelo plano de controle do Azure, autenticado e auditado |
| **Pipeline** | [`.github/workflows/devsecops.yml`](.github/workflows/devsecops.yml): Gitleaks · Semgrep · pytest · compose · Trivy (config e imagem) · SBOM · push no ACR · deploy · smoke test | cada push passa pelos portões; deploy só da `main`, via OIDC (sem senha de nuvem) |
| **Observabilidade** | [`observabilidade/`](observabilidade): métricas na API (`/metrics` com Bearer), alertas Prometheus, dashboard Grafana como código | latência, tráfego, erros e saturação + inferência e negócio |

## Como executar

### Local (Docker)
```bash
python scripts/preparar_segredos.py        # gera .env e o token do Prometheus (fora do git)
docker compose up -d --build               # API em http://localhost:8000
docker compose --profile observabilidade up -d   # + Prometheus :9090 e Grafana :3000 (só localhost)
```

### Testes e portões de segurança (os mesmos do pipeline)
```bash
pip install -r requirements-dev.txt && pytest -q
gitleaks dir . && trivy config . --severity HIGH,CRITICAL && semgrep scan --config p/python --config p/javascript --config p/secrets --config p/dockerfile --config p/terraform --error
```

### Infraestrutura (Azure, uma vez)
Num ACR novo ainda não existe imagem para o Container App, então a criação tem três etapas (a mesma ordem dos planos
em `docs/evidencias/terraform_plan_*.txt`). Cada plano é revisado por uma pessoa antes do `apply`.
```bash
az login && az account set -s <assinatura>
bash infra/bootstrap/criar_backend.sh brazilsouth           # state remoto (Storage + Entra ID)
python scripts/preparar_segredos.py --subscription <assinatura>   # infra/terraform.tfvars (fora do git)
cd infra && terraform init -backend-config=backend.hcl
# a) base: grupo, Log Analytics, ACR, identidades, papéis, ambiente e OIDC (sem o Container App)
terraform plan -out=base.tfplan -target=azurerm_container_app_environment.env -target=azurerm_role_assignment.app_pull \
  -target=azurerm_role_assignment.github_push -target=azurerm_role_assignment.github_deploy \
  -target=azurerm_federated_identity_credential.github_main
terraform apply base.tfplan
# b) GitHub Secrets (identificadores) + PUBLICAR_IMAGEM=true; um push na main publica a 1ª imagem (tag = commit)
powershell -File ../scripts/configurar_github.ps1
# c) Container App com essa imagem e, depois, deploy automático (DEPLOY_HABILITADO=true)
terraform plan -out=app.tfplan -var tag_imagem=<commit publicado> && terraform apply app.tfplan
powershell -File ../scripts/configurar_github.ps1 -HabilitarDeploy
```
O script cadastra em **Settings → Secrets and variables → Actions** `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
`AZURE_SUBSCRIPTION_ID`, `ACR_NOME`, `ACA_NOME`, `AZURE_RG` (secrets) e as variables `PUBLICAR_IMAGEM` e
`DEPLOY_HABILITADO`. A partir daí todo push na `main` é implantado.

### Observabilidade apontando para a nuvem
```bash
python scripts/preparar_segredos.py --fqdn <fqdn do terraform output>
docker compose --profile observabilidade up -d
python scripts/gerar_carga.py --url https://ca-vigiavia-prod.happywave-0bf5b4c3.brazilsouth.azurecontainerapps.io --concorrencia 16 --duracao 300   # dispara o alerta de latência
```

## Custos (preços reais, Brazil South)

`python scripts/estimar_custo.py --data-ptax 2026-11-04` consulta a Azure Retail Prices API e a PTAX do Banco Central:
**MVP ≈ US$ 15,61/mês (R$ 85,53)** — coberto pelo crédito do Azure for Students. Na escala de cidade (4 réplicas,
20 milhões de requisições e 20 GB de logs por mês): **US$ 258,77/mês (R$ 1.417,51)**. Detalhes em
[`docs/custos.json`](docs/custos.json). (Até 09/11 o script usava a faixa gratuita da ingestão de logs e a cidade saía
US$ 189,77.)

## Evidências

| O quê | Onde |
|---|---|
| Deploy automático com todos os portões verdes | [run 41953126657](https://github.com/akiramrt/vigiavia-mvp/actions/runs/41953126657) |
| **Execução barrada**: o Trivy achou 4 CVEs HIGH no `python-multipart 0.0.17` e o deploy não aconteceu | [run 41953686302](https://github.com/akiramrt/vigiavia-mvp/actions/runs/41953686302) · [trecho do log](docs/evidencias/trivy_execucao_barrada.txt) |
| **Execução corrigida**: versão 0.0.33, deploy e smoke test conferindo o commit no ar | [run 41954209587](https://github.com/akiramrt/vigiavia-mvp/actions/runs/41954209587) |
| Azure: ingress só HTTPS, ACR sem admin, OIDC só da `main`, RBAC mínimo, state protegido | [azure_configuracao.txt](docs/evidencias/azure_configuracao.txt) |
| GitHub Secrets e Variables (só identificadores; nenhuma senha de nuvem) | [github_configuracao.txt](docs/evidencias/github_configuracao.txt) |
| Planos do Terraform revisados antes de cada `apply` | [docs/evidencias](docs/evidencias) (`terraform_plan_*.txt`) |
| Dashboard dos sinais de ouro e alerta disparado sob carga | [docs/evidencias/img](docs/evidencias/img) e [relatório (PDF)](docs/relatorio/VigiaVia_Secure_DevOps.pdf) |
| Achado da observabilidade: reinício sob carga → timeout das probes (não resolveu) → causa raiz: inferência no event loop → correção com teste de regressão → reteste sem reinício | [plano das probes](docs/evidencias/terraform_plan_6_probes.txt) · [commit b12e62e](https://github.com/akiramrt/vigiavia-mvp/commit/b12e62e) · [reteste](docs/evidencias/reteste_carga_pos_correcao.txt) |
| Registros brutos dos testes de carga (rodada inicial, 2 reinícios no reteste das probes, 0 após a correção) | [docs/evidencias/carga](docs/evidencias/carga) |
| Relatório gerado a partir destas evidências | [`docs/relatorio/gerar_relatorio.py`](docs/relatorio/gerar_relatorio.py) + [`modelo.html`](docs/relatorio/modelo.html) |

Os IDs de assinatura, tenant e identidades do Azure foram mascarados nas evidências em 09/11/2026 (são identificadores,
não credenciais).

## Segurança e LGPD (resumo)

* **Segredos:** nenhum no código, na imagem ou no state versionado; `METRICS_TOKEN` entra como segredo do Container App;
  o GitHub usa OIDC (identidade federada) — não há senha de nuvem para vazar.
* **Dados pessoais:** a API **não guarda imagens enviadas**; um relato guarda só lat/lon, severidade e o recorte da via
  (SQLite dentro do container, região Brazil South). Logs da plataforma no Log Analytics por 30 dias.
* **Fora do Azure, direto do navegador:** tiles do mapa (OpenStreetMap), bibliotecas (unpkg, jsDelivr) e, só quando o
  cidadão busca um endereço, o texto digitado (Nominatim, no exterior: transferência internacional, LGPD art. 33). Há
  alternativa sem envio (tocar no mapa ou GPS). Em produção: servir tudo pelo próprio domínio, em Brazil South.
* **Limitação do MVP:** a fila da zeladoria não tem login (qualquer pessoa com o link pode validar ou descartar), para a
  banca testar o fluxo; em produção, login dos agentes (Entra ID) e trilha de auditoria.
* **Responsabilidade compartilhada:** Microsoft cuida do hardware, rede física, hipervisor, plataforma do Container Apps,
  TLS do ingress; a equipe cuida do código, da imagem e suas dependências, identidades/RBAC, segredos, dados e configuração.

## Pitch (Business Intelligence & Startup Development)

[Modelo de negócio e viabilidade](docs/pitch/modelo_de_negocio.md) (números reproduzíveis em
[`viabilidade.py`](docs/pitch/viabilidade.py)) · [roteiro de 5 minutos](docs/pitch/roteiro.md) ·
[guia de gravação](docs/pitch/guia_gravacao.md) · [slides (PowerPoint)](docs/pitch/VigiaVia_Pitch.pptx), gerados por [`gerar_pptx.js`](docs/pitch/gerar_pptx.js).

## Licença
Código sob **AGPL-3.0**. Modelo treinado com Ultralytics YOLO (AGPL-3.0) sobre o RDD2022 (CC BY-SA 4.0).
