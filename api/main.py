"""
VigiaVia — API do MVP (detecção de buracos + fila de zeladoria), pronta para produção em container.

Endpoints
  GET   /health                      liveness/readiness (usado pelo Container Apps e pelo pipeline)
  GET   /metrics                     métricas Prometheus (4 sinais de ouro) — exige Bearer METRICS_TOKEN
  GET   /v1/modelo                   ficha do modelo em produção
  POST  /v1/deteccoes                imagem (multipart) -> buracos detectados; a imagem é descartada (LGPD)
  POST  /v1/relatos                  cria/atualiza relato; < RAIO_DEDUP_M de um relato aberto = confirmação
  GET   /v1/relatos                  fila da zeladoria ordenada por prioridade
  PATCH /v1/relatos/{id}             validação humana (confirmado / descartado / resolvido)
  GET   /v1/relatos/{id}/evidencia   recorte da via usado como evidência
  GET   /                            interface web (cidadão + zeladoria)

Configuração por variáveis de ambiente (nenhum segredo no código ou na imagem):
  VIGIAVIA_DB, VIGIAVIA_PESOS, VIGIAVIA_RAIO_DEDUP_M, VIGIAVIA_THREADS, VIGIAVIA_SEMEAR_DEMO, METRICS_TOKEN
"""
from __future__ import annotations

import base64
import hmac
import math
import os
import sqlite3
import sys
import time
import uuid
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from anyio import CapacityLimiter, to_thread
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from vigiavia import __version__, config, severidade  # noqa: E402
from vigiavia.detector_onnx import DetectorONNX  # noqa: E402
from vigiavia.tipos import ZONA_TRAJETORIA  # noqa: E402

BANCO = Path(os.getenv("VIGIAVIA_DB", RAIZ / "dados" / "vigiavia.db"))
RAIO_DEDUP_M = float(os.getenv("VIGIAVIA_RAIO_DEDUP_M", "15"))
TAM_MAX_IMAGEM = 8 * 1024 * 1024
MAX_PIXELS = 40_000_000
PESO_SEV = {"baixa": 1, "media": 2, "alta": 3}
ESTADO: dict = {}

# ----------------------------------------------------------------------------- métricas (4 sinais de ouro)
REQUISICOES = Counter("http_requests_total", "Requisições HTTP (tráfego e erros)", ["method", "rota", "status"])
LATENCIA = Histogram("http_request_duration_seconds", "Latência das requisições HTTP", ["method", "rota"],
                     buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8))
EM_ANDAMENTO = Gauge("http_requests_em_andamento", "Requisições em processamento (saturação)")
INFERENCIA = Histogram("vigiavia_inferencia_segundos", "Tempo de inferência do modelo",
                       buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6))
DETECCOES = Counter("vigiavia_buracos_detectados_total", "Buracos detectados em imagens enviadas")
RELATOS = Counter("vigiavia_relatos_total", "Relatos recebidos", ["resultado"])


# ----------------------------------------------------------------------------- banco
def _db() -> sqlite3.Connection:
    con = sqlite3.connect(BANCO, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _iniciar_banco() -> None:
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    with closing(_db()) as con, con:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("""
            CREATE TABLE IF NOT EXISTS relatos (
                id TEXT PRIMARY KEY, criado_em TEXT, atualizado_em TEXT,
                lat REAL, lon REAL, severidade TEXT, confianca_max REAL,
                confirmacoes INTEGER, origem TEXT, status TEXT, modelo TEXT,
                evidencia BLOB, observacao TEXT)""")


def _semear_demo(det: DetectorONNX) -> None:
    """Relatos de demonstração (coordenadas simuladas na Bela Vista/SP) para a fila não abrir vazia."""
    with closing(_db()) as con:
        if con.execute("SELECT COUNT(*) FROM relatos").fetchone()[0]:
            return
    base = (-23.560345, -46.650508)
    desloc = [(0, 0), (0.0011, -0.0007), (-0.0009, 0.0012), (0.0016, 0.0015), (-0.0014, -0.0013),
              (0.0021, -0.0004), (-0.0004, 0.0024), (0.0027, 0.0009)]
    amostras = sorted((RAIZ / "api" / "static" / "amostras").glob("*.jpg"))
    for k, p in enumerate(amostras[: len(desloc)]):
        img = cv2.imread(str(p))
        dets = det.detectar(img)
        if not dets:
            continue
        d = max(dets, key=lambda x: x.confianca)
        h, w = img.shape[:2]
        mx, my = 0.25 * (d.x2 - d.x1), 0.25 * (d.y2 - d.y1)
        rec = img[int(max(0, d.y1 - my)):int(min(h, d.y2 + my)), int(max(0, d.x1 - mx)):int(min(w, d.x2 + mx))]
        esc = min(1.0, 320 / max(rec.shape[:2]))
        rec = cv2.resize(rec, None, fx=esc, fy=esc) if esc < 1 else rec
        _, buf = cv2.imencode(".jpg", rec, [cv2.IMWRITE_JPEG_QUALITY, 80])
        sev = max((x.severidade for x in dets), key=PESO_SEV.get)
        _gravar_relato(base[0] + desloc[k][0], base[1] + desloc[k][1], sev, d.confianca, "demonstracao",
                       det.nome, buf.tobytes())


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    _iniciar_banco()
    det = DetectorONNX(config.pesos_padrao(), conf=config.conf_padrao())
    det.detectar(np.zeros((640, 640, 3), np.uint8))           # aquece o modelo
    ESTADO["detector"] = det
    # no máximo N inferências ao mesmo tempo; as demais esperam a vez sem gastar CPU (0,5 vCPU no Azure)
    ESTADO["limite_inferencias"] = CapacityLimiter(int(os.getenv("VIGIAVIA_INFERENCIAS_SIMULTANEAS", "2")))
    if os.getenv("VIGIAVIA_SEMEAR_DEMO", "true").lower() == "true":
        _semear_demo(det)
    yield


app = FastAPI(title="VigiaVia", version=__version__, lifespan=ciclo_de_vida, docs_url="/docs", redoc_url=None,
              description="Detecção de buracos em vias públicas integrada à fila de zeladoria.")


# ----------------------------------------------------------------------------- middleware: métricas + segurança
# media-src precisa de blob:: o vídeo que o cidadão escolhe é aberto no próprio navegador (URL.createObjectURL).
# Sem isso, o default-src 'self' faz o navegador recusar o vídeo (a foto passa, porque img-src já tem blob:).
CSP = ("default-src 'self'; img-src 'self' data: blob: https://tile.openstreetmap.org https://unpkg.com; "
       "media-src 'self' blob:; "
       "script-src 'self' https://unpkg.com https://cdn.jsdelivr.net 'wasm-unsafe-eval'; "
       "style-src 'self' 'unsafe-inline' https://unpkg.com; connect-src 'self' https://cdn.jsdelivr.net https://nominatim.openstreetmap.org; "
       "worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")


@app.middleware("http")
async def observar_e_proteger(request: Request, call_next):
    EM_ANDAMENTO.inc()
    inicio = time.perf_counter()
    status = 500
    try:
        resposta = await call_next(request)
        status = resposta.status_code
    finally:
        EM_ANDAMENTO.dec()
        rota = request.scope.get("route")
        nome_rota = getattr(rota, "path", "nao_mapeada")
        if nome_rota != "/metrics":
            LATENCIA.labels(request.method, nome_rota).observe(time.perf_counter() - inicio)
            REQUISICOES.labels(request.method, nome_rota, str(status)).inc()
    resposta.headers.update({
        "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(self), geolocation=(self), microphone=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains", "Content-Security-Policy": CSP,
        "Cross-Origin-Opener-Policy": "same-origin"})
    return resposta


# ----------------------------------------------------------------------------- modelos de dados
class CaixaDetectada(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confianca: float
    severidade: Literal["baixa", "media", "alta"]
    indice_severidade: float
    area_relativa: float
    na_trajetoria: bool
    classe: str = "buraco"


class RespostaDeteccao(BaseModel):
    modelo: str
    limiar_confianca: float
    largura: int
    altura: int
    tempo_inferencia_ms: float
    quantidade: int
    deteccoes: list[CaixaDetectada]


class NovoRelato(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    severidade: Literal["baixa", "media", "alta"]
    confianca_max: float = Field(ge=0, le=1)
    origem: Literal["cidadao", "camera_veicular", "robo"] = "cidadao"
    modelo: str | None = Field(default=None, max_length=80)
    evidencia_jpg_base64: str | None = Field(default=None, max_length=300_000,
                                             description="apenas o recorte da via (≤ 200 KB)")


class Validacao(BaseModel):
    status: Literal["confirmado", "descartado", "resolvido"]
    observacao: str | None = Field(default=None, max_length=280)


# ----------------------------------------------------------------------------- utilidades
def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def prioridade(sev: str, confirmacoes: int) -> float:
    return round(PESO_SEV[sev] * (1 + math.log2(max(1, confirmacoes))), 3)


def _publico(row: sqlite3.Row) -> dict:
    d = {k: row[k] for k in row.keys() if k != "evidencia"}
    d["tem_evidencia"] = row["evidencia"] is not None
    d["prioridade"] = prioridade(row["severidade"], row["confirmacoes"])
    return d


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _gravar_relato(lat, lon, sev, conf, origem, modelo, evidencia) -> dict:
    agora = _agora()
    with closing(_db()) as con, con:
        con.execute("BEGIN IMMEDIATE")                      # serializa a deduplicação (sem corrida)
        abertos = con.execute("SELECT * FROM relatos WHERE status IN ('pendente', 'confirmado')").fetchall()
        prox = sorted(((distancia_m(lat, lon, r["lat"], r["lon"]), r) for r in abertos), key=lambda t: t[0])
        if prox and prox[0][0] <= RAIO_DEDUP_M:
            dist, r = prox[0]
            nova_sev = max(r["severidade"], sev, key=PESO_SEV.get)
            con.execute("""UPDATE relatos SET confirmacoes = confirmacoes + 1, atualizado_em = ?, severidade = ?,
                           confianca_max = MAX(confianca_max, ?), evidencia = COALESCE(evidencia, ?) WHERE id = ?""",
                        (agora, nova_sev, conf, evidencia, r["id"]))
            novo = con.execute("SELECT * FROM relatos WHERE id = ?", (r["id"],)).fetchone()
            return {"mensagem": f"Buraco já registrado a {dist:.0f} m — confirmação adicionada", "duplicado": True,
                    "relato": _publico(novo)}
        rid = str(uuid.uuid4())
        con.execute("INSERT INTO relatos VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, 'pendente', ?, ?, NULL)",
                    (rid, agora, agora, lat, lon, sev, conf, origem, modelo, evidencia))
        novo = con.execute("SELECT * FROM relatos WHERE id = ?", (rid,)).fetchone()
    return {"mensagem": "Relato criado e enviado para validação da zeladoria", "duplicado": False,
            "relato": _publico(novo)}


# ----------------------------------------------------------------------------- endpoints
@app.get("/health")
def health() -> dict:
    det: DetectorONNX = ESTADO["detector"]
    return {"status": "ok", "versao": __version__, "commit": os.getenv("VIGIAVIA_COMMIT", "dev"),
            "modelo": det.nome, "limiar_confianca": det.conf}


@app.get("/metrics", include_in_schema=False)
def metricas(request: Request) -> Response:
    token = os.getenv("METRICS_TOKEN", "")
    enviado = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if token and not hmac.compare_digest(enviado.encode(), token.encode()):
        return PlainTextResponse("não autorizado", status_code=401)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/modelo")
def modelo() -> dict:
    det: DetectorONNX = ESTADO["detector"]
    op = config.operacao()
    return {"modelo": det.nome, "limiar_confianca": det.conf, "imgsz": det.imgsz,
            "onnx": "/modelos/vigiavia_buracos.onnx", "metricas_teste": op.get("metricas_teste"),
            "severidade": {"horizonte": severidade.HORIZONTE, "limiar_media": severidade.LIMIARES[0],
                           "limiar_alta": severidade.LIMIARES[1]},
            "zona_trajetoria": ZONA_TRAJETORIA}


def _decodificar_e_detectar(dados: bytes, conf: float | None):
    """Trabalho pesado de CPU (decodificação + inferência ONNX). Roda numa thread de trabalho, FORA do event
    loop: assim o /health (liveness probe) e o /metrics continuam respondendo com a CPU saturada.
    No teste de carga do MVP publicado, rodar isto direto na rota async travava o event loop e o Azure
    reiniciava o container por falha da liveness probe."""
    img = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_COLOR)
    if img is None or img.shape[0] * img.shape[1] > MAX_PIXELS:
        return None
    altura, largura = img.shape[:2]
    t0 = time.perf_counter()
    caixas = ESTADO["detector"].detectar(img, conf=conf)
    return caixas, altura, largura, time.perf_counter() - t0  # a imagem morre aqui (LGPD: minimização)


@app.post("/v1/deteccoes", response_model=RespostaDeteccao)
async def detectar(imagem: UploadFile = File(...),
                   conf: float | None = Query(default=None, ge=0.01, le=0.99)) -> RespostaDeteccao:
    dados = await imagem.read(TAM_MAX_IMAGEM + 1)
    if len(dados) > TAM_MAX_IMAGEM:
        raise HTTPException(413, "Imagem maior que 8 MB")
    resultado = await to_thread.run_sync(_decodificar_e_detectar, dados, conf,
                                         limiter=ESTADO.get("limite_inferencias"))
    del dados                                                 # nada é persistido (LGPD: minimização)
    if resultado is None:
        raise HTTPException(422, "Arquivo não é uma imagem válida (ou é grande demais)")
    caixas, altura, largura, dt = resultado
    det: DetectorONNX = ESTADO["detector"]
    INFERENCIA.observe(dt)
    DETECCOES.inc(len(caixas))
    return RespostaDeteccao(modelo=det.nome, limiar_confianca=conf or det.conf, largura=largura, altura=altura,
                            tempo_inferencia_ms=round(dt * 1000, 1), quantidade=len(caixas),
                            deteccoes=[CaixaDetectada(**c.para_dict()) for c in caixas])


@app.post("/v1/relatos", status_code=201)
def criar_relato(relato: NovoRelato) -> dict:
    evidencia = None
    if relato.evidencia_jpg_base64:
        try:
            evidencia = base64.b64decode(relato.evidencia_jpg_base64, validate=True)
        except ValueError as exc:
            raise HTTPException(422, "evidencia_jpg_base64 inválida") from exc
        if len(evidencia) > 200_000 or cv2.imdecode(np.frombuffer(evidencia, np.uint8), cv2.IMREAD_COLOR) is None:
            raise HTTPException(422, "Evidência deve ser um JPEG de até 200 KB (só o recorte da via)")
    r = _gravar_relato(relato.lat, relato.lon, relato.severidade, relato.confianca_max, relato.origem,
                       relato.modelo, evidencia)
    RELATOS.labels("confirmacao" if r["duplicado"] else "novo").inc()
    return r


@app.get("/v1/relatos")
def listar_relatos(status: str | None = None, limite: int = Query(default=200, le=1000)) -> dict:
    with closing(_db()) as con:
        if status:
            linhas = con.execute("SELECT * FROM relatos WHERE status = ?", (status,)).fetchall()
        else:
            linhas = con.execute("SELECT * FROM relatos").fetchall()
    itens = sorted((_publico(r) for r in linhas), key=lambda d: (-d["prioridade"], d["criado_em"]))
    return {"total": len(itens), "relatos": itens[:limite]}


@app.patch("/v1/relatos/{rid}")
def validar_relato(rid: str, validacao: Validacao) -> dict:
    with closing(_db()) as con, con:
        cur = con.execute("UPDATE relatos SET status = ?, observacao = ?, atualizado_em = ? WHERE id = ?",
                          (validacao.status, validacao.observacao, _agora(), rid))
        if cur.rowcount == 0:
            raise HTTPException(404, "Relato não encontrado")
        r = con.execute("SELECT * FROM relatos WHERE id = ?", (rid,)).fetchone()
    return _publico(r)


@app.get("/v1/relatos/{rid}/evidencia")
def evidencia(rid: str) -> Response:
    with closing(_db()) as con:
        r = con.execute("SELECT evidencia FROM relatos WHERE id = ?", (rid,)).fetchone()
    if r is None or r["evidencia"] is None:
        raise HTTPException(404, "Sem evidência para este relato")
    return Response(content=r["evidencia"], media_type="image/jpeg")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(RAIZ / "api" / "static" / "index.html")


app.mount("/static", StaticFiles(directory=RAIZ / "api" / "static"), name="static")
app.mount("/modelos", StaticFiles(directory=RAIZ / "modelos"), name="modelos")
