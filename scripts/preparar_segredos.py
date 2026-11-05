"""
Prepara os arquivos LOCAIS de configuração sensível (todos ignorados pelo git):
  .env                                   METRICS_TOKEN e GRAFANA_SENHA aleatórios e fortes
  observabilidade/segredos/metrics_token token lido pelo Prometheus
  infra/terraform.tfvars                 subscription_id + metrics_token (se --subscription for informado)
  observabilidade/prometheus/alvos_azure.json  alvo do Prometheus (se --fqdn for informado; não é segredo)

Uso:
    python scripts/preparar_segredos.py --subscription <id>
    python scripts/preparar_segredos.py --fqdn <app>.azurecontainerapps.io
"""
from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def ler_env() -> dict[str, str]:
    env = RAIZ / ".env"
    if not env.exists():
        return {}
    return dict(l.split("=", 1) for l in env.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subscription")
    ap.add_argument("--fqdn")
    args = ap.parse_args()

    env = ler_env()
    env.setdefault("METRICS_TOKEN", secrets.token_urlsafe(32))
    env.setdefault("GRAFANA_SENHA", secrets.token_urlsafe(18))
    (RAIZ / ".env").write_text("".join(f"{k}={v}\n" for k, v in env.items()), encoding="utf-8")

    seg = RAIZ / "observabilidade" / "segredos"
    seg.mkdir(parents=True, exist_ok=True)
    (seg / "metrics_token").write_text(env["METRICS_TOKEN"], encoding="utf-8")

    if args.subscription:
        (RAIZ / "infra" / "terraform.tfvars").write_text(
            f'subscription_id = "{args.subscription}"\nmetrics_token   = "{env["METRICS_TOKEN"]}"\n', encoding="utf-8")
    if args.fqdn:
        alvos = [{"targets": [args.fqdn], "labels": {"ambiente": "azure"}}]
        (RAIZ / "observabilidade" / "prometheus" / "alvos_azure.json").write_text(json.dumps(alvos, indent=2),
                                                                                  encoding="utf-8")
    print("Arquivos locais prontos (fora do git): .env, observabilidade/segredos/metrics_token"
          + (", infra/terraform.tfvars" if args.subscription else "")
          + (", observabilidade/prometheus/alvos_azure.json" if args.fqdn else ""))


if __name__ == "__main__":
    main()
