"""Testes do contrato da API, do detector ONNX, das métricas e dos cabeçalhos de segurança."""
import base64
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    os.environ["VIGIAVIA_DB"] = str(tmp_path_factory.mktemp("db") / "teste.db")
    os.environ["VIGIAVIA_SEMEAR_DEMO"] = "false"
    os.environ["METRICS_TOKEN"] = "token-de-teste"
    from fastapi.testclient import TestClient
    import api.main as m
    m.BANCO = Path(os.environ["VIGIAVIA_DB"])
    with TestClient(m.app) as c:
        yield c


def _jpg(img) -> bytes:
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def test_health_e_cabecalhos_de_seguranca(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    for h in ("Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Strict-Transport-Security"):
        assert h in r.headers


def test_csp_permite_abrir_video_escolhido_pelo_cidadao(cliente):
    # Regressão: sem media-src com blob:, o navegador recusava o vídeo aberto por URL.createObjectURL.
    csp = cliente.get("/").headers["Content-Security-Policy"]
    diretivas = dict(d.strip().split(" ", 1) for d in csp.split(";") if d.strip())
    assert "blob:" in diretivas["media-src"].split()
    assert "blob:" not in diretivas["default-src"].split()
    # a busca de endereço do relato (Nominatim) é a única origem externa nova liberada para fetch
    assert diretivas["connect-src"].split() == ["'self'", "https://cdn.jsdelivr.net", "https://nominatim.openstreetmap.org"]


def test_detector_onnx_encontra_buraco_em_amostra_real(cliente):
    amostra = RAIZ / "api" / "static" / "amostras" / "rdd2022_India_003366.jpg"
    r = cliente.post("/v1/deteccoes", files={"imagem": (amostra.name, amostra.read_bytes(), "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["quantidade"] >= 1


def test_deteccao_em_imagem_sem_buraco(cliente):
    cinza = np.full((480, 640, 3), 128, np.uint8)
    r = cliente.post("/v1/deteccoes", files={"imagem": ("x.jpg", _jpg(cinza), "image/jpeg")})
    corpo = r.json()
    assert corpo["largura"] == 640 and corpo["altura"] == 480 and corpo["quantidade"] == 0


def test_rejeita_arquivo_que_nao_e_imagem(cliente):
    r = cliente.post("/v1/deteccoes", files={"imagem": ("x.txt", b"nao sou imagem", "text/plain")})
    assert r.status_code == 422


def test_relatos_proximos_viram_confirmacao(cliente):
    evid = base64.b64encode(_jpg(np.zeros((60, 80, 3), np.uint8))).decode()
    base = {"lat": -23.561414, "lon": -46.655881, "severidade": "media", "confianca_max": 0.8,
            "evidencia_jpg_base64": evid}
    assert cliente.post("/v1/relatos", json=base).json()["duplicado"] is False
    r2 = cliente.post("/v1/relatos", json={**base, "lat": -23.561460, "severidade": "alta"}).json()
    assert r2["duplicado"] is True and r2["relato"]["confirmacoes"] == 2 and r2["relato"]["severidade"] == "alta"
    assert cliente.post("/v1/relatos", json={**base, "lat": -23.570}).json()["duplicado"] is False
    assert cliente.get("/v1/relatos").json()["relatos"][0]["id"] == r2["relato"]["id"]


def test_evidencia_invalida_e_rejeitada(cliente):
    lixo = base64.b64encode(b"isto nao e jpeg").decode()
    r = cliente.post("/v1/relatos", json={"lat": 0, "lon": 0, "severidade": "baixa", "confianca_max": 0.5,
                                          "evidencia_jpg_base64": lixo})
    assert r.status_code == 422


def test_validacao_humana(cliente):
    rid = cliente.get("/v1/relatos").json()["relatos"][0]["id"]
    r = cliente.patch(f"/v1/relatos/{rid}", json={"status": "confirmado", "observacao": "vistoria ok"})
    assert r.status_code == 200 and r.json()["status"] == "confirmado"
    assert cliente.patch("/v1/relatos/inexistente", json={"status": "resolvido"}).status_code == 404


def test_metricas_exigem_token(cliente):
    assert cliente.get("/metrics").status_code == 401
    r = cliente.get("/metrics", headers={"Authorization": "Bearer token-de-teste"})
    assert r.status_code == 200
    assert "http_request_duration_seconds" in r.text and "http_requests_total" in r.text


def test_health_responde_durante_inferencia_lenta(cliente, monkeypatch):
    """Regressão do teste de carga: a inferência não pode bloquear o event loop. Antes, com a CPU saturada,
    o /health (usado pela liveness probe) esperava atrás das detecções e o container era reiniciado."""
    import threading
    import time

    import api.main as m

    def lenta(img, conf=None):
        time.sleep(1.5)                                  # simula a CPU saturada
        return []

    monkeypatch.setattr(m.ESTADO["detector"], "detectar", lenta)
    preta = _jpg(np.zeros((64, 64, 3), np.uint8))
    t = threading.Thread(target=lambda: cliente.post("/v1/deteccoes", files={"imagem": ("p.jpg", preta, "image/jpeg")}))
    t.start()
    time.sleep(0.3)                                      # a detecção já está em andamento
    t0 = time.perf_counter()
    assert cliente.get("/health").status_code == 200
    espera = time.perf_counter() - t0
    t.join()
    assert espera < 0.5, f"/health esperou {espera:.2f} s atrás da inferência"
