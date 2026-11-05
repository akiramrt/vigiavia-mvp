"""
Gera tráfego realista contra o MVP (detecções de imagens reais + leituras da fila) para alimentar o
dashboard dos 4 sinais de ouro e, com concorrência alta, saturar o container e disparar o alerta de latência.

Uso:
    python scripts/gerar_carga.py --url https://<app>.azurecontainerapps.io --concorrencia 4 --duracao 120
    python scripts/gerar_carga.py --url ... --concorrencia 16 --duracao 300      # dispara VigiaViaLatenciaAlta
"""
from __future__ import annotations

import argparse
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

AMOSTRAS = sorted((Path(__file__).resolve().parents[1] / "api" / "static" / "amostras").glob("*.jpg"))


def trabalhador(url: str, fim: float, semente: int) -> list[tuple[int, float]]:
    rng = random.Random(semente)
    sessao = requests.Session()
    resultados = []
    while time.time() < fim:
        t0 = time.perf_counter()
        try:
            if rng.random() < 0.85:
                img = rng.choice(AMOSTRAS)
                r = sessao.post(f"{url}/v1/deteccoes", files={"imagem": (img.name, img.read_bytes(), "image/jpeg")},
                                timeout=30)
            else:
                r = sessao.get(f"{url}/v1/relatos", timeout=30)
            resultados.append((r.status_code, time.perf_counter() - t0))
        except requests.RequestException:
            resultados.append((0, time.perf_counter() - t0))
    return resultados


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--concorrencia", type=int, default=4)
    ap.add_argument("--duracao", type=int, default=120, help="segundos")
    args = ap.parse_args()
    fim = time.time() + args.duracao
    with ThreadPoolExecutor(args.concorrencia) as ex:
        todos = [r for lst in ex.map(lambda i: trabalhador(args.url.rstrip("/"), fim, i), range(args.concorrencia))
                 for r in lst]
    lat = sorted(t for _, t in todos)
    ok = sum(1 for s, _ in todos if 200 <= s < 300)
    print(f"{len(todos)} requisições em {args.duracao}s ({len(todos) / args.duracao:.1f} req/s) · "
          f"{ok / max(1, len(todos)):.1%} OK · latência p50 {statistics.median(lat):.2f}s · "
          f"p95 {lat[int(0.95 * (len(lat) - 1))]:.2f}s")


if __name__ == "__main__":
    main()
