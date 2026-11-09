"""
Estimativa de custo mensal do VigiaVia no Azure, com PREÇOS REAIS da Azure Retail Prices API (pública)
e a cotação PTAX do dólar do Banco Central do Brasil. Gera docs/custos.json e imprime a tabela.

Cenários:
  MVP     — 1 réplica (0,5 vCPU / 1 GiB) sempre ligada, ~5% do tempo processando requisições
  Cidade  — 4 réplicas (1 vCPU / 2 GiB), 40% do tempo ativas (ex.: 300 ônibus enviando imagens)

Uso: python scripts/estimar_custo.py [--regiao brazilsouth] [--data-ptax 2026-11-04]
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

API = "https://prices.azure.com/api/retail/prices"
SEG_MES = 730 * 3600
GRATIS = {"vcpu_s": 180_000, "gib_s": 360_000, "req": 2_000_000}   # cota gratuita mensal do Container Apps


def preco(filtro: str, medidor: str, faixa_paga: bool = False) -> float:
    """Preço de varejo do medidor. Com faixa_paga, ignora a faixa gratuita (preço 0) de medidores escalonados,
    como a ingestão do Log Analytics (0–5 GB grátis, depois US$/GB): a franquia é descontada no cálculo do cenário.
    Até 09/11/2026 o script pegava a faixa gratuita e zerava esse item no cenário Cidade."""
    for tentativa in range(5):
        r = requests.get(API, params={"$filter": filtro}, timeout=30)
        if r.status_code == 200:
            itens = [i for i in r.json()["Items"] if i["meterName"] == medidor and i["type"] == "Consumption"]
            if faixa_paga:
                itens = [i for i in itens if i["retailPrice"] > 0] or itens
            if itens:
                return float(min(itens, key=lambda i: i.get("tierMinimumUnits", 0))["retailPrice"])
            raise SystemExit(f"Medidor não encontrado: {medidor}")
        time.sleep(3 * (tentativa + 1))
    raise SystemExit(f"API de preços indisponível para {medidor}")


def ptax(ate: date) -> tuple[float, str]:
    """PTAX de venda do dólar no dia `ate` ou no último dia útil anterior."""
    for d in range(0, 7):
        dia = ate - timedelta(days=d)
        url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@d)"
               f"?@d='{dia:%m-%d-%Y}'&$format=json")
        v = requests.get(url, timeout=30).json().get("value", [])
        if v:
            return float(v[-1]["cotacaoVenda"]), dia.isoformat()
    return 5.5, "valor de referência"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regiao", default="brazilsouth")
    ap.add_argument("--data-ptax", type=date.fromisoformat, default=date.today(),
                    help="dia da cotação (AAAA-MM-DD); o relatório usa 2026-11-04")
    args = ap.parse_args()
    reg = args.regiao
    aca = f"serviceName eq 'Azure Container Apps' and armRegionName eq '{reg}'"
    p = {
        "vcpu_ativa": preco(aca, "Standard vCPU Active Usage"),
        "vcpu_ociosa": preco(aca, "Standard vCPU Idle Usage"),
        "mem_ativa": preco(aca, "Standard Memory Active Usage"),
        "mem_ociosa": preco(aca, "Standard Memory Idle Usage"),
        "req_milhao": preco(aca, "Standard Requests"),
        "acr_dia": preco(f"serviceName eq 'Container Registry' and armRegionName eq '{reg}'", "Basic Registry Unit"),
        "log_gb": preco(f"serviceName eq 'Log Analytics' and armRegionName eq '{reg}'", "Analytics Logs Data Ingestion",
                        faixa_paga=True),
        "blob_gb": preco(f"serviceName eq 'Storage' and armRegionName eq '{reg}' and skuName eq 'Hot LRS'",
                         "Hot LRS Data Stored"),
    }
    cot, dia = ptax(args.data_ptax)

    def cenario(nome, replicas, vcpu, gib, frac_ativa, req_mes, log_gb):
        ativo_vcpu = replicas * vcpu * SEG_MES * frac_ativa
        ocioso_vcpu = replicas * vcpu * SEG_MES * (1 - frac_ativa)
        gib_s = replicas * gib * SEG_MES
        itens = {
            "Container Apps — vCPU ativa": max(0, ativo_vcpu - GRATIS["vcpu_s"]) * p["vcpu_ativa"],
            "Container Apps — vCPU ociosa": ocioso_vcpu * p["vcpu_ociosa"],
            "Container Apps — memória": max(0, gib_s - GRATIS["gib_s"]) * p["mem_ativa"],
            "Container Apps — requisições": max(0, req_mes - GRATIS["req"]) / 1e6 * p["req_milhao"],
            "Container Registry Basic": p["acr_dia"] * 30.4,
            "Log Analytics (ingestão)": max(0, log_gb - 5) * p["log_gb"],   # 5 GB/mês gratuitos
            "Storage do state (Terraform)": 0.01 * p["blob_gb"],
        }
        total = sum(itens.values())
        return {"cenario": nome, "replicas": replicas, "vcpu": vcpu, "gib": gib, "fracao_ativa": frac_ativa,
                "requisicoes_mes": req_mes, "itens_usd": {k: round(v, 2) for k, v in itens.items()},
                "total_usd": round(total, 2), "total_brl": round(total * cot, 2)}

    res = {"regiao": reg, "precos_usd": p, "ptax": cot, "data_ptax": dia, "fonte": "prices.azure.com + BCB PTAX",
           "cenarios": [cenario("MVP (1 réplica 0,5 vCPU / 1 GiB, 5% ativa)", 1, 0.5, 1, 0.05, 300_000, 0.5),
                        cenario("Cidade (4 réplicas 1 vCPU / 2 GiB, 40% ativas)", 4, 1, 2, 0.40, 20_000_000, 20)]}
    destino = Path(__file__).resolve().parents[1] / "docs" / "custos.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"PTAX {cot:.4f} ({dia})")
    for c in res["cenarios"]:
        print(f"\n{c['cenario']}")
        for k, v in c["itens_usd"].items():
            print(f"  {k:32s} US$ {v:8.2f}")
        print(f"  {'TOTAL / mês':32s} US$ {c['total_usd']:8.2f}  (R$ {c['total_brl']:.2f})")


if __name__ == "__main__":
    main()
