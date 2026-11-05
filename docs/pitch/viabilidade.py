"""Viabilidade do VigiaVia (BI & Startup Development): premissas explícitas, preço, margem, projeção e pedido.

Custo de nuvem: docs/custos.json (Azure Retail Prices API, Brazil South). Câmbio do euro: PTAX do Banco Central.
Uso: python docs/pitch/viabilidade.py   -> imprime o resumo e grava docs/pitch/viabilidade.json
"""
import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def ptax_euro() -> tuple[float, str]:
    """PTAX de venda do euro (fechamento) no último dia útil disponível."""
    dia = date.today()
    for _ in range(10):
        url = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoMoedaDia(moeda=@m,dataCotacao=@d)"
               f"?@m='EUR'&@d='{dia:%m-%d-%Y}'&$format=json")
        try:
            v = json.load(urllib.request.urlopen(url, timeout=20))["value"]
            if v:
                return float(v[-1]["cotacaoVenda"]), dia.isoformat()
        except Exception:  # noqa: BLE001 - sem rede: tenta o dia anterior e, no fim, usa o valor de referência
            pass
        dia -= timedelta(days=1)
    return 6.40, "referência (sem acesso à PTAX)"


custos = json.loads((RAIZ / "docs" / "custos.json").read_text(encoding="utf-8"))
nuvem_cidade_mes = next(c for c in custos["cenarios"] if c["cenario"].startswith("Cidade"))["total_brl"]
nuvem_mvp_mes = next(c for c in custos["cenarios"] if c["cenario"].startswith("MVP"))["total_brl"]
eur, dia_eur = ptax_euro()

P = {
    # referência de preço: piloto público da vialytics no condado de Louth (Irlanda): €17.500/ano para 1.691 km
    "referencia_eur_km_ano": round(17500 / 1691, 2),
    "preco_km_ano_brl": 60.0,           # posicionado logo abaixo da referência convertida pela PTAX do euro
    "km_pavimentados_sp": 13000,        # TCM-SP (2021): ~17 mil km de vias, ~13 mil km pavimentados
    "subprefeituras_sp": 32,
    "km_por_dispositivo": 40,           # 1 celular embarcado em viatura/ônibus parceiro a cada 40 km de malha
    "custo_dispositivo_brl": 900,       # Android de entrada + suporte veicular
    "vida_util_dispositivo_anos": 3,
    "suporte_por_subprefeitura_ano_brl": 3000,
    "piloto": {"meses": 6, "valor_brl": 150000, "veiculos": 10},
    "custos_fixos_ano_brl": {"2027": 336000, "2028": 480000, "2029": 720000},  # 3 sócios + despesas; contratações em 2028-29
    "cidades_medias_km": 1000,
}
km_sub = P["km_pavimentados_sp"] / P["subprefeituras_sp"]
custo_var_km = {
    "nuvem": nuvem_cidade_mes * 12 / P["km_pavimentados_sp"],
    "dispositivos": P["custo_dispositivo_brl"] / P["km_por_dispositivo"] / P["vida_util_dispositivo_anos"],
    "suporte": P["suporte_por_subprefeitura_ano_brl"] / km_sub,
}
cv = sum(custo_var_km.values())
margem = (P["preco_km_ano_brl"] - cv) / P["preco_km_ano_brl"]

# cenário: piloto CPSI na Subprefeitura Sé (1º semestre/2027) -> contrato de fornecimento -> outras cidades
cenario = {
    "2027": {"descricao": "piloto CPSI (Sé, 6 meses) + 4 subprefeituras no 2º semestre", "km": 4 * km_sub, "fracao_ano": 0.5,
             "extra_brl": P["piloto"]["valor_brl"],
             "custo_extra_brl": P["piloto"]["veiculos"] * P["custo_dispositivo_brl"] + P["suporte_por_subprefeitura_ano_brl"] / 2},
    "2028": {"descricao": "16 subprefeituras de SP + 3 cidades médias", "km": 16 * km_sub + 3 * P["cidades_medias_km"], "fracao_ano": 1},
    "2029": {"descricao": "SP inteira (32 subprefeituras) + 10 cidades médias", "km": 32 * km_sub + 10 * P["cidades_medias_km"], "fracao_ano": 1},
}
proj, acumulado, pior = {}, 0.0, 0.0
for ano, c in cenario.items():
    receita = c["km"] * P["preco_km_ano_brl"] * c["fracao_ano"] + c.get("extra_brl", 0)
    variavel = c["km"] * cv * c["fracao_ano"] + c.get("custo_extra_brl", 0)
    resultado = receita - variavel - P["custos_fixos_ano_brl"][ano]
    acumulado += resultado
    pior = min(pior, acumulado)
    proj[ano] = {"cenario": c["descricao"], "km_monitorados": round(c["km"]), "receita_brl": round(receita),
                 "custo_variavel_brl": round(variavel), "custo_fixo_brl": P["custos_fixos_ano_brl"][ano],
                 "resultado_brl": round(resultado), "caixa_acumulado_brl": round(acumulado)}

sp_inteira = P["km_pavimentados_sp"] * P["preco_km_ano_brl"]
res = {
    "premissas": P, "ptax_euro": eur, "data_ptax_euro": dia_eur,
    "referencia_brl_km_ano": round(P["referencia_eur_km_ano"] * eur, 2),
    "nuvem_brl_mes": {"mvp": nuvem_mvp_mes, "sp_inteira": nuvem_cidade_mes},
    "custo_variavel_brl_km_ano": {k: round(v, 2) for k, v in custo_var_km.items()} | {"total": round(cv, 2)},
    "margem_bruta": round(margem, 3),
    "preco_subprefeitura_mes_brl": round(km_sub * P["preco_km_ano_brl"] / 12),
    "sp_inteira_brl_ano": sp_inteira,
    "sp_inteira_vs_tapa_buraco_2019": round(sp_inteira / 144e6, 4),   # R$ 144 mi empenhados em tapa-buraco em 2019
    "ponto_equilibrio_km_2029": round(P["custos_fixos_ano_brl"]["2029"] / (P["preco_km_ano_brl"] - cv)),
    "projecao": proj,
    "necessidade_caixa_brl": round(-pior),
    "pedido_investimento_brl": 300000,
}
(RAIZ / "docs" / "pitch" / "viabilidade.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Referência vialytics: €{P['referencia_eur_km_ano']}/km/ano x PTAX {eur:.4f} ({dia_eur}) = R$ {res['referencia_brl_km_ano']}/km/ano")
print(f"Preço VigiaVia: R$ {P['preco_km_ano_brl']:.0f}/km/ano = R$ {res['preco_subprefeitura_mes_brl']}/mês por subprefeitura (~{km_sub:.0f} km)")
print(f"Custo variável: R$ {cv:.2f}/km/ano {res['custo_variavel_brl_km_ano']} -> margem bruta {margem:.1%}")
print(f"SP inteira: R$ {sp_inteira:,.0f}/ano = {res['sp_inteira_vs_tapa_buraco_2019']:.2%} dos R$ 144 mi de tapa-buraco (2019)")
print(f"Ponto de equilíbrio (custo fixo de 2029): {res['ponto_equilibrio_km_2029']:,} km monitorados")
for ano, p in proj.items():
    print(f"{ano}: {p['km_monitorados']:>6,} km | receita R$ {p['receita_brl']:>9,} | resultado R$ {p['resultado_brl']:>9,} | caixa R$ {p['caixa_acumulado_brl']:>9,}")
print(f"Necessidade de caixa até o equilíbrio: R$ {res['necessidade_caixa_brl']:,} -> pedido R$ {res['pedido_investimento_brl']:,}")
