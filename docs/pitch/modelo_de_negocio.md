# VigiaVia — modelo de negócio e viabilidade

> Base do pitch de **Business Intelligence & Startup Development** (FIAP GS 2026.2 · CitizenTech · 4ES).
> Números reproduzíveis em [`viabilidade.py`](viabilidade.py) → [`viabilidade.json`](viabilidade.json).
> Equipe: Deivison Pertel (RM 550803) · Eduardo Akira Murata (RM 98713) · Wesley Souza de Oliveira (RM 97874).

## 1. O problema, com evidência

| Dado | Fonte |
|---|---|
| **113,1 mil pedidos de tapa-buraco** em São Paulo em 2025 (177,3 mil em 2023); a prefeitura reconhece que um mesmo ponto gera vários chamados | SMSUB, via [BNews SP](https://www.bnewssaopaulo.com.br/noticias/politica/mesmo-apos-recapeamento-sp-registra-quase-52-mil-pedidos-de-tapa-buraco.html) |
| **R$ 144 milhões** empenhados só em operações de tapa-buraco em 2019 | [CartaCapital](https://www.cartacapital.com.br/?p=73147) |
| **475 motociclistas** morreram no trânsito da capital em 2025 — o maior grupo de vítimas (quem mais sente o buraco) | Infosiga, via [Portal do Trânsito](https://www.portaldotransito.com.br/noticias/fiscalizacao-e-legislacao/estatisticas/capital-paulista-tem-2o-maior-numero-de-mortes-no-transito-em-2025/) |
| **~17 mil km** de vias, **~13 mil km pavimentados** em SP | [TCM-SP](https://egcportalantigo.tcm.sp.gov.br/images/conteudo-palestras/17-tardes-conhecimento/tardes-de-conhecimento-apresentacao-eduardo-carvalho.pdf) |

Hoje a cidade **espera o chamado**: o buraco só entra na fila quando alguém liga para o 156, muitas vezes várias pessoas
para o mesmo buraco, sem foto padronizada, sem severidade e sem prioridade.

## 2. Proposta de valor

**Detectar buracos automaticamente com as câmeras que já circulam pela cidade e entregar à zeladoria um relato único,
georreferenciado e priorizado por buraco — com privacidade (nenhuma foto inteira guardada) e validação humana.**

| Para quem | Ganho |
|---|---|
| Prefeitura / subprefeitura (zeladoria) | fila única sem duplicados, priorizada por severidade e confirmações; evidência fotográfica para a ordem de serviço e para auditoria |
| Cidadão (motociclista, ciclista, pedestre, motorista) | alerta de “buraco à frente” no celular e um jeito de relatar em segundos, sem cadastro |
| Frotas parceiras (ônibus, entregas, viaturas da própria prefeitura) | alerta para os condutores e menos dano aos veículos, em troca de rodar com um celular embarcado |

## 3. Quem paga, quem usa e como chega

| | |
|---|---|
| **Quem paga** | A **prefeitura** (subprefeituras / zeladoria), por assinatura SaaS: **R$ 60 por km de via monitorado por ano** — cerca de **R$ 2 mil/mês por subprefeitura** (~406 km). Referência internacional: o piloto público da vialytics em Louth (Irlanda) custou €17.500/ano para 1.691 km ≈ €10,35/km/ano ≈ **R$ 63/km/ano** (PTAX do euro de 05/11/2026) |
| **Quem usa** | Agentes de zeladoria (painel e fila); cidadãos (grátis, web/celular); motoristas de frotas parceiras (celular embarcado = sensor) |
| **Como chega (go-to-market)** | 1) **Piloto via CPSI** (Contrato Público de Solução Inovadora, Marco Legal das Startups, LC 182/2021): até **R$ 1,6 mi**, 12 meses, e depois contrato de fornecimento de até R$ 8 mi sem nova licitação ([Demarest](https://www.demarest.com.br/marco-legal-das-startups-e-sancionado/)) · 2) expansão às 32 subprefeituras de SP · 3) cidades médias com o caso de SP, consórcios intermunicipais e integração com canais que as prefeituras já usam (156, Colab — presente em mais de 100 prefeituras) |
| **Por que agora** | Modelo validado lá fora: a vialytics atende **600+ municípios** na Europa e nos EUA; no Brasil a cidade ainda depende do chamado manual |

## 4. Custos e viabilidade (premissas em `viabilidade.py`)

| Item | Valor |
|---|---|
| Nuvem (Azure, preço oficial) | MVP **R$ 85,53/mês**; SP inteira **R$ 1.417,51/mês** (4 réplicas, 20 mi requisições/mês, 20 GB/mês de logs) |
| Custo variável por km/ano | nuvem R$ 1,31 + celulares embarcados R$ 7,50 + suporte R$ 7,38 = **R$ 16,19** |
| **Margem bruta** | **73,0 %** |
| SP inteira (13 mil km) | **R$ 780 mil/ano = 0,54 %** do que a cidade empenhou só em tapa-buraco em 2019 |
| Ponto de equilíbrio | **~16,4 mil km monitorados** (custo fixo de 2029) — pouco mais que a malha pavimentada de SP |

> Revisão de 09/11/2026: o custo de nuvem de “SP inteira” passou de R$ 1.039,54 para R$ 1.417,51/mês, porque o
> `scripts/estimar_custo.py` usava a faixa gratuita da ingestão do Log Analytics (US$ 0/GB) em vez da faixa paga
> (US$ 4,60/GB acima de 5 GB). A margem caiu de 73,6 % para 73,0 %; preço, pedido e ano do equilíbrio não mudam.

| Ano | Cenário | km | Receita | Resultado | Caixa acumulado |
|---|---|---|---|---|---|
| 2027 | piloto CPSI na Sé (6 meses, R$ 150 mil) + 4 subprefeituras no 2º semestre | 1.625 | R$ 198.750 | −R$ 160.907 | −R$ 160.907 |
| 2028 | 16 subprefeituras + 3 cidades médias | 9.500 | R$ 570.000 | −R$ 63.834 | −R$ 224.741 |
| 2029 | SP inteira + 10 cidades médias | 23.000 | R$ 1.380.000 | **+R$ 287.559** | +R$ 62.818 |

## 5. Indicadores

| Negócio | Impacto no cidadão |
|---|---|
| km monitorados e subprefeituras/cidades contratantes | tempo entre detecção e reparo (dias) |
| receita recorrente anual (ARR) e margem bruta | % de chamados duplicados evitados |
| renovação de contratos (churn) | buracos detectados por km rodado |
| custo de aquisição por contrato (ciclo do CPSI) | precisão das detecções confirmadas pela zeladoria |
| custo por km monitorado | (longo prazo) sinistros com motociclistas nas vias monitoradas |

**ODS:** 11 (11.2 transporte seguro; 11.3 participação cidadã) · 9 (9.1 infraestrutura de qualidade) · 3 (3.6 reduzir mortes no trânsito).

## 6. O pedido

1. **Parceiro:** piloto de **6 meses na Subprefeitura Sé** via CPSI — **R$ 150 mil** (10 celulares em viaturas da zeladoria,
   ~406 km, integração com a fila de ordens de serviço). Metas: **−30 % de chamados duplicados** e **ordem de serviço em menos de 48 h**
   após a detecção, com precisão confirmada ≥ 80 %.
2. **Investimento:** **R$ 300 mil** de pré-seed — cobre a necessidade de caixa de R$ 225 mil até o equilíbrio em 2029, com folga.

## 7. Riscos e respostas

| Risco | Resposta |
|---|---|
| Ciclo de venda ao setor público | CPSI encurta o caminho; piloto pequeno, com metas e evidência |
| Privacidade (LGPD) | a imagem é descartada após a detecção; o relato guarda só o recorte da via e a localização; validação humana |
| Qualidade do modelo em ruas brasileiras | precisão medida em produção pela confirmação da zeladoria; novos dados de cada piloto melhoram o modelo |
| Concorrente internacional chegar | foco local: integração com 156/Colab, dados de ruas brasileiras, preço em reais e contratação via CPSI |
