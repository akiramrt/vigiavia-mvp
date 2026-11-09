# Evidências do teste de carga e do diagnóstico do reinício (04 e 05/11/2026)

Arquivos brutos dos testes contra o MVP publicado (horário de Brasília), gerados por `scripts/gerar_carga.py` e por
consultas ao Prometheus da equipe. `docs/relatorio/gerar_relatorio.py` lê estes arquivos para montar a seção 6 do
relatório. Foram convertidos para UTF-8; o conteúdo é o original.

| Arquivo | O que é |
|---|---|
| `carga.log` | Rodada com 16 clientes por 7 minutos: requisições, taxa, sucesso e latências p50/p95 |
| `primeiro_firing.txt` | Segundos de carga até o primeiro alerta em FIRING no Prometheus (114 s) |
| `alertas.json` | Resposta de `/api/v1/alerts` do Prometheus no momento dos prints (Figura 6 do relatório) |
| `inicio_antes.txt` | `process_start_time_seconds` da API antes do reteste das probes |
| `carga2.log`, `amostras2.txt` | Reteste depois de subir o timeout das probes para 5 s. O `process_start_time_seconds` muda duas vezes (amostras de 23:49:45 e 23:52:10 sem resposta, depois um novo início): **2 reinícios**, hipótese refutada |
| `carga3.log`, `amostras3.txt`, `reinicios3.txt` | Reteste depois da correção (inferência fora do event loop): o mesmo `process_start_time_seconds` do início ao fim, `/health` sempre 200 e **0 reinícios** |
| `smoke.txt` | Saída do smoke test do deploy corrigido (run 41954209587); `***` são GitHub Secrets mascarados pelo Actions |

Nos demais arquivos de `docs/evidencias`, os IDs de assinatura, tenant e identidades do Azure foram mascarados em
09/11/2026 (por exemplo, `cf0f…`). São identificadores, não credenciais, mas não precisam ficar públicos.
