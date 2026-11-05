"""Configuração de operação (modelo e limiar escolhidos na avaliação) + variáveis de ambiente."""
from __future__ import annotations

import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ARQ_OPERACAO = RAIZ / "configs" / "operacao.json"
PESOS_PADRAO = RAIZ / "modelos" / "vigiavia_buracos.onnx"
CONF_PADRAO = 0.35


def operacao() -> dict:
    try:
        return json.loads(ARQ_OPERACAO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pesos_padrao() -> Path:
    return Path(os.getenv("VIGIAVIA_PESOS", PESOS_PADRAO))


def conf_padrao() -> float:
    return float(operacao().get("conf", CONF_PADRAO))
