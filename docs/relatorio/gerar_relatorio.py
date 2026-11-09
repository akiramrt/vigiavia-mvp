"""Preenche docs/relatorio/modelo.html com as evidências reais do repositório e gera o PDF (Chrome via Playwright).

Uso: python docs/relatorio/gerar_relatorio.py      (requer: pip install playwright; Google Chrome instalado)
Entradas: docs/evidencias (Azure, Trivy, prints), docs/evidencias/carga (testes de carga), docs/custos.json.
"""
import html
import json
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

SAIDA = Path(__file__).resolve().parent
REPO_DIR = SAIDA.parents[1]
OBS = REPO_DIR / "docs" / "evidencias" / "carga"


def br(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def esc(t: str) -> str:
    return html.escape(t, quote=False)


# ---------------------------------------------------------------- Azure (trechos)
secoes = {}
for bloco in (REPO_DIR / "docs/evidencias/azure_configuracao.txt").read_text(encoding="utf-8").split("\n## ")[1:]:
    titulo, _, corpo = bloco.partition("\n")
    secoes[titulo.strip()] = corpo.strip()
quero = ["Ingress", "Probes", "Registro de imagens", "Identidade federada", "Papéis", "State remoto"]
azure = []
for chave in quero:
    for titulo, corpo in secoes.items():
        if titulo.startswith(chave):
            corpo = re.sub(r"/subscriptions/[0-9a-f-]+", "/subscriptions/…", corpo)
            azure.append(f"## {titulo}\n{corpo}")
azure_txt = "\n\n".join(azure)

# ---------------------------------------------------------------- Trivy (run barrado) como tabela
trivy = (REPO_DIR / "docs/evidencias/trivy_execucao_barrada.txt").read_text(encoding="utf-8")
linhas = [l for l in trivy.splitlines() if l.startswith("│")]
cves, atual = [], None
for l in linhas:
    cel = [c.strip() for c in l.strip("│").split("│")]
    if len(cel) < 7:
        continue
    if cel[1].startswith("CVE-"):
        atual = {"cve": cel[1], "fix": cel[5], "titulo": cel[6]}
        cves.append(atual)
    elif atual and cel[6] and not cel[6].startswith("https://"):
        atual["titulo"] += " " + cel[6]
total = re.search(r"Total: \d+ \(HIGH: \d+, CRITICAL: \d+\)", trivy).group(0)
trivy_html = ["<div style='break-inside:avoid'><table><tr><th>Biblioteca</th><th>CVE</th><th>Severidade</th><th>Instalada</th><th>Corrigida em</th><th>Descrição (Trivy)</th></tr>"]
for c in cves:
    titulo = re.sub(r"^python-multipart: (Python-Multipart: |python-multipart: )?", "", c["titulo"])
    trivy_html.append(f"<tr><td>python-multipart</td><td><a href='https://avd.aquasec.com/nvd/{c['cve'].lower()}'>{c['cve']}</a></td>"
                      f"<td class='no'>HIGH</td><td>0.0.17</td><td>{c['fix']}</td><td>{esc(titulo)}</td></tr>")
trivy_html.append("</table>")
trivy_html.append(f"<pre>Python (python-pkg)\n{total}\n##[error]Process completed with exit code 1.   → push no ACR e deploy NÃO executados</pre></div>")

# ---------------------------------------------------------------- smoke test do deploy corrigido
smoke = re.sub(r" {3,}", "  ", (OBS / "smoke.txt").read_text(encoding="utf-8").strip())

# ---------------------------------------------------------------- carga e alertas
carga = ([l for l in (OBS / "carga.log").read_text(encoding="utf-8", errors="replace").splitlines() if "req/s" in l]
         or ["0 requisições em 0s (0 req/s) · 0% OK · latência p50 0s · p95 0s"])[-1]
m = re.search(r"(\d+) requisi.+? em (\d+)s \(([\d.]+) req/s\).+?([\d.]+)% OK.+?p50 ([\d.]+)s.+?p95 ([\d.]+)s", carga)
n_req, dur, rps, ok, p50, p95 = m.groups()
carga_res = (f"{br(int(n_req), 0)} requisições em {dur} s ({br(float(rps), 1)} req/s), {br(float(ok), 1)}% respondidas com sucesso, "
             f"latência p50 de {br(float(p50))} s e p95 de {br(float(p95))} s")
alertas = json.loads((OBS / "alertas.json").read_text(encoding="utf-8"))["data"]["alerts"]
disparados = [a for a in alertas if a["state"] == "firing"]
partes = []
for a in disparados:
    desde = datetime.fromisoformat(a["activeAt"].replace("Z", "+00:00")).astimezone().strftime("%H:%M:%S")
    partes.append(f"<code>{a['labels']['alertname']}</code> (valor {br(float(a['value']))} s)")
alertas_txt = ("No momento dos prints, o Prometheus mostrava em <b>FIRING</b>: " + "; ".join(partes) + "."
               if partes else "")
primeiro = (OBS / "primeiro_firing.txt").read_text(encoding="utf-8").strip() if (OBS / "primeiro_firing.txt").exists() else ""
if primeiro:
    alertas_txt = f"O primeiro alerta disparou aos {primeiro} s de carga. " + alertas_txt

# ---------------------------------------------------------------- reteste depois da correção (inferência fora do event loop)
l3 = [l for l in (OBS / "carga3.log").read_text(encoding="utf-8", errors="replace").splitlines() if "req/s" in l][-1]
n3, dur3, rps3, ok3, _, p95_3 = re.search(
    r"(\d+) requisi.+? em (\d+)s \(([\d.]+) req/s\).+?([\d.]+)% OK.+?p50 ([\d.]+)s.+?p95 ([\d.]+)s", l3).groups()
amostras = (OBS / "amostras3.txt").read_text(encoding="utf-8").splitlines()
inicios = set(re.findall(r"inicio=([0-9.e+]+)", "\n".join(amostras)))
filas = [float(x) for x in re.findall(r"fila=([0-9.]+)", "\n".join(amostras))]
saude = re.findall(r"health=(\d+):([0-9.]+)", "\n".join(amostras))
lat_h = sorted(float(t) for _, t in saude)
reinicios = int((OBS / "reinicios3.txt").read_text(encoding="utf-8").strip())
assert len(inicios) == 1 and reinicios == 0 and all(c == "200" for c, _ in saude), "o reteste não confirma a correção"
reteste3 = (f"{br(int(n3), 0)} requisições ({br(float(rps3), 1)} req/s), <b>{br(float(ok3), 1)}% com sucesso</b>, p95 de {br(float(p95_3))} s "
            f"(a CPU continua no limite: escalar ainda é necessário), fila de até {max(filas):.0f} requisições, "
            f"<b><code>/health</code> sempre 200</b> com latência mediana de {br(__import__('statistics').median(lat_h))} s e máxima de {br(lat_h[-1])} s "
            f"nas {len(saude)} medições, e <b>nenhum reinício</b> (<code>restartCount = 0</code>; "
            f"<code>process_start_time_seconds</code> constante). Amostras em <code>docs/evidencias/reteste_carga_pos_correcao.txt</code>")

# ---------------------------------------------------------------- custos
cus = json.loads((REPO_DIR / "docs/custos.json").read_text(encoding="utf-8"))
mvp, cid = cus["cenarios"]
t = [f"<table><tr><th>Item (Brazil South)</th><th>{esc(mvp['cenario'])}</th><th>{esc(cid['cenario'])}</th></tr>"]
for item in mvp["itens_usd"]:
    t.append(f"<tr><td>{esc(item)}</td><td>US$ {br(mvp['itens_usd'][item])}</td><td>US$ {br(cid['itens_usd'][item])}</td></tr>")
t.append(f"<tr><th>Total mensal</th><th>US$ {br(mvp['total_usd'])} · R$ {br(mvp['total_brl'])}</th>"
         f"<th>US$ {br(cid['total_usd'])} · R$ {br(cid['total_brl'])}</th></tr>")
t.append(f"<tr><td>Requisições/mês consideradas</td><td>{br(mvp['requisicoes_mes'], 0)}</td><td>{br(cid['requisicoes_mes'], 0)}</td></tr></table>")
custos_html = "<div style='break-inside:avoid'>" + "".join(t) + "</div>"

repro = """# 1) Local (Docker): a mesma stack do pipeline
python scripts/preparar_segredos.py              # .env e token do Prometheus (fora do git)
docker compose up -d --build                     # API em http://localhost:8000
docker compose --profile observabilidade up -d   # + Prometheus :9090 e Grafana :3000 (só 127.0.0.1)

# 2) Portões de segurança na máquina (os mesmos do pipeline)
pip install -r requirements-dev.txt && pytest -q
gitleaks git . && trivy config . --severity HIGH,CRITICAL
semgrep scan --config p/python --config p/javascript --config p/secrets --config p/dockerfile --config p/terraform --error

# 3) Nuvem, uma vez (o Container App precisa de uma imagem que ainda não existe num ACR novo)
az login && bash infra/bootstrap/criar_backend.sh brazilsouth     # state remoto (Storage + Entra ID)
python scripts/preparar_segredos.py --subscription <assinatura>   # infra/terraform.tfvars (fora do git)
cd infra && terraform init -backend-config=backend.hcl
#  a) base: grupo, Log Analytics, ACR, identidades, papéis, ambiente e OIDC (sem o Container App)
terraform plan -out=base.tfplan -target=azurerm_container_app_environment.env -target=azurerm_role_assignment.app_pull \\
  -target=azurerm_role_assignment.github_push -target=azurerm_role_assignment.github_deploy \\
  -target=azurerm_federated_identity_credential.github_main
terraform apply base.tfplan
#  b) secrets do GitHub + PUBLICAR_IMAGEM=true; um push na main publica a 1ª imagem (tag = commit)
powershell -File ..\\scripts\\configurar_github.ps1
#  c) Container App com essa imagem; depois, deploy automático ligado
terraform plan -out=app.tfplan -var tag_imagem=<commit publicado> && terraform apply app.tfplan
powershell -File ..\\scripts\\configurar_github.ps1 -HabilitarDeploy

# 4) Daí em diante: git push na main = portões de segurança + deploy automático + smoke test"""

# corta a área branca abaixo do conteúdo nos prints do Prometheus
from PIL import Image, ImageChops
for f in (REPO_DIR / "docs/evidencias/img").glob("prometheus_*.png"):
    im = Image.open(f).convert("RGB")
    caixa = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if caixa and caixa[3] < im.height - 24:
        im.crop((0, 0, im.width, caixa[3] + 16)).save(f)

valores = {
    "{{URL}}": "https://ca-vigiavia-prod.happywave-0bf5b4c3.brazilsouth.azurecontainerapps.io",
    "{{REPO}}": "https://github.com/akiramrt/vigiavia-mvp",
    "{{RUN_CORRIGIDO}}": "41954209587",
    "{{DATA}}": datetime.now().strftime("%d/%m/%Y"),
    "<pre>{{TRIVY}}</pre>": "".join(trivy_html),
    "{{AZURE}}": esc(azure_txt),
    "{{SMOKE}}": esc(smoke),
    "{{CARGA_CFG}}": "16 clientes simultâneos por 7 minutos (85% <code>POST /v1/deteccoes</code> com imagens reais de amostra e 15% <code>GET /v1/relatos</code>)",
    "{{CARGA_RES}}": carga_res,
    "{{RETESTE3}}": reteste3,
    "{{ALERTAS_TXT}}": alertas_txt,
    "{{RPS}}": br(float(rps), 1),
    "{{PTAX}}": br(cus["ptax"], 4),
    "{{PTAX_DATA}}": datetime.strptime(cus["data_ptax"], "%Y-%m-%d").strftime("%d/%m/%Y"),
    "{{CUSTOS}}": custos_html,
    "{{MVP_USD}}": br(mvp["total_usd"]), "{{MVP_BRL}}": br(mvp["total_brl"]),
    "{{CID_USD}}": br(cid["total_usd"]), "{{CID_BRL}}": br(cid["total_brl"]),
    "{{CID_LOG_USD}}": br(cid["itens_usd"]["Log Analytics (ingestão)"]), "{{LOG_GB_USD}}": br(cus["precos_usd"]["log_gb"]),
    "{{REPRO}}": esc(repro),
}
doc = (SAIDA / "modelo.html").read_text(encoding="utf-8")
for k, v in valores.items():
    doc = doc.replace(k, v)
restantes = re.findall(r"\{\{[A-Z_]+\}\}", doc)
assert not restantes, restantes
(SAIDA / "relatorio.html").write_text(doc, encoding="utf-8")

with sync_playwright() as p:
    nav = p.chromium.launch(channel="chrome", headless=True)
    pg = nav.new_page()
    pg.goto((SAIDA / "relatorio.html").as_uri(), wait_until="networkidle")
    pg.pdf(path=str(SAIDA / "VigiaVia_Secure_DevOps.pdf"), format="A4", print_background=True, prefer_css_page_size=True)
    nav.close()
print("PDF gerado:", SAIDA / "VigiaVia_Secure_DevOps.pdf")
