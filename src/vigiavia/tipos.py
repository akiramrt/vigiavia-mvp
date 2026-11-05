"""Tipos e geometria do VigiaVia, sem dependência de framework de IA (roda no container de produção)."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

# Trapézio da trajetória à frente do veículo, em coordenadas normalizadas (x, y).
ZONA_TRAJETORIA = ((0.12, 1.00), (0.40, 0.58), (0.60, 0.58), (0.88, 1.00))


@dataclass
class Deteccao:
    x1: float
    y1: float
    x2: float
    y2: float
    confianca: float
    severidade: str
    indice_severidade: float
    area_relativa: float
    na_trajetoria: bool
    classe: str = "buraco"

    @property
    def caixa(self) -> tuple[float, float, float, float]:
        return self.x1, self.y1, self.x2, self.y2

    def para_dict(self) -> dict:
        d = asdict(self)
        for k in ("x1", "y1", "x2", "y2"):
            d[k] = round(float(d[k]), 1)
        d["confianca"] = round(float(d["confianca"]), 4)
        d["indice_severidade"] = round(float(d["indice_severidade"]), 5)
        d["area_relativa"] = round(float(d["area_relativa"]), 5)
        return d


def zona_em_pixels(largura: int, altura: int, zona=ZONA_TRAJETORIA) -> np.ndarray:
    return np.array([(x * largura, y * altura) for x, y in zona], dtype=np.int32)


def dentro_do_poligono(ponto: tuple[float, float], poligono: np.ndarray) -> bool:
    """Ray casting (evita depender do OpenCV só para isso)."""
    x, y = ponto
    dentro = False
    n = len(poligono)
    for i in range(n):
        x1, y1 = poligono[i]
        x2, y2 = poligono[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro


def sobreposicao(a: tuple, b: tuple) -> float:
    """max(IoU, interseção / menor área): alta também quando uma caixa está DENTRO da outra."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if inter <= 0:
        return 0.0
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[2] - b[0]) * (b[3] - b[1])
    return max(inter / (aa + ab - inter), inter / max(1e-9, min(aa, ab)))


def suprimir_aninhadas(deteccoes: list[Deteccao], limiar: float = 0.7) -> list[Deteccao]:
    mantidas: list[Deteccao] = []
    for d in sorted(deteccoes, key=lambda x: -x.confianca):
        if all(sobreposicao(d.caixa, m.caixa) < limiar for m in mantidas):
            mantidas.append(d)
    return mantidas
