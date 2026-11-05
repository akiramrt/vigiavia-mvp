# Roteiro do pitch — VigiaVia (até 5 minutos)

> Business Intelligence & Startup Development · Prof. André Maluf · FIAP GS 2026.2.
> ~680 palavras ≈ 4min40s em ritmo de apresentação. Números e fontes: [modelo_de_negocio.md](modelo_de_negocio.md).
> **Regra da banca:** a equipe aparece e conduz o pitch; a demo é o MVP real na URL pública (nada de slide imitando tela).

| Tempo | Bloco | Quem fala | O que aparece |
|---|---|---|---|
| 0:00 | 1. O cidadão e o problema | Deivison | câmera → tela **O problema** |
| 0:30 | 2. Solução e proposta de valor | Deivison | câmera → tela **A solução** |
| 1:00 | 3. Demonstração do MVP | Eduardo | câmera (3 s) → **gravação real do MVP** |
| 2:30 | 4. Modelo de negócio | Wesley | câmera → tela **Modelo de negócio** |
| 3:30 | 5. Indicadores e ODS | Wesley | tela **Indicadores** (com a câmera em miniatura) |
| 4:15 | 6. Viabilidade e pedido | Deivison | câmera → tela **Viabilidade e pedido** |
| 4:50 | Fechamento | os três | os três na câmera → tela final com nomes e RMs |

Troquem os blocos entre vocês se fizer mais sentido; só mantenham os tempos.

---

## 1. O cidadão e o problema — Deivison (0:00–0:30)

> Imagine voltar do trabalho de moto, à noite, e cair num buraco que outras pessoas já tinham denunciado.
> Em 2025, São Paulo recebeu **113 mil pedidos de tapa-buraco** — e a própria prefeitura reconhece que o mesmo buraco
> gera vários chamados. Só em 2019, a cidade empenhou **144 milhões de reais** em tapa-buraco. E quem anda de moto é o
> mais exposto: **475 motociclistas** morreram no trânsito da capital em 2025.

*Tela "O problema" entra a partir de "113 mil".*

## 2. Solução e proposta de valor — Deivison (0:30–1:00)

> Nós somos o **VigiaVia**. Em vez de esperar o chamado, usamos as câmeras que já circulam pela cidade — o celular do
> cidadão, de ônibus, de entregadores e das viaturas da prefeitura — para **detectar buracos automaticamente** com visão
> computacional. A zeladoria recebe **um único relato por buraco**, com localização, foto da via e prioridade.
> Sem guardar rosto, sem guardar foto inteira, e sempre com validação humana.

*Tela "A solução" a partir de "detectar buracos".*

## 3. Demonstração do MVP — Eduardo (1:00–2:30)

> *(câmera)* Eu sou o Eduardo, e este é o VigiaVia funcionando de verdade, na URL pública, no Azure.
>
> *(gravação do MVP — ver [guia_gravacao.md](guia_gravacao.md))* Na visão do cidadão, eu abro a câmera — ou envio um
> vídeo gravado na rua. O modelo detecta o buraco em tempo real e avisa: **"atenção, buraco à frente"**, com a severidade.
> Com um toque, envio o relato: vai só o recorte da via e a localização; nenhuma foto inteira é guardada.
> Agora, a visão da zeladoria: os relatos chegam numa **fila priorizada** por severidade e confirmações, e aparecem no
> mapa. Se outra pessoa relatar o mesmo buraco, ele não vira um chamado novo: vira uma **confirmação** e sobe na fila.
> O agente valida com um clique, e o relato vira ordem de serviço. E tudo isso roda em produção, com deploy automático e
> segurança no pipeline: se aparece uma dependência vulnerável, o deploy é barrado.

## 4. Modelo de negócio — Wesley (2:30–3:30)

> *(câmera)* Eu sou o Wesley. **Quem paga é a prefeitura**: uma assinatura de **60 reais por quilômetro de via monitorado
> por ano** — cerca de 2 mil reais por mês por subprefeitura. É o patamar de quem já faz isso lá fora: a vialytics atende
> mais de 600 municípios na Europa e nos Estados Unidos, por cerca de 63 reais por quilômetro.
> **Quem usa:** o cidadão, de graça; os agentes de zeladoria; e frotas parceiras, que rodam com um celular embarcado em
> troca do alerta para os seus motoristas.
> **Como chegamos:** pelo Marco Legal das Startups. Um Contrato Público de Solução Inovadora permite à prefeitura
> contratar um piloto de até 1,6 milhão de reais e, se der certo, seguir para o contrato definitivo. Começamos por uma
> subprefeitura de São Paulo, expandimos para as 32 e levamos o caso para cidades médias.

*Tela "Modelo de negócio" a partir de "Quem paga".*

## 5. Indicadores e ODS — Wesley (3:30–4:15)

> Medimos o sucesso em duas frentes. **No negócio:** quilômetros monitorados, receita recorrente, margem bruta — de 74% —
> e renovação de contratos. **No cidadão:** o tempo entre a detecção e o reparo, a porcentagem de chamados duplicados
> evitados, os buracos detectados por quilômetro e a precisão confirmada pela zeladoria. Esses indicadores ligam o
> VigiaVia a três Objetivos de Desenvolvimento Sustentável: cidades sustentáveis, o **ODS 11**; infraestrutura de
> qualidade, o **ODS 9**; e a redução de mortes no trânsito, o **ODS 3**.

## 6. Viabilidade e pedido — Deivison (4:15–4:50)

> E é viável. Nossa nuvem custa **85 reais por mês** no MVP e cerca de **mil reais por mês** para cobrir São Paulo
> inteira. Monitorar os 13 mil quilômetros pavimentados da cidade custaria **780 mil reais por ano** — meio por cento do
> que a cidade empenhou só em tapa-buraco em 2019. Com margem de 74%, o ponto de equilíbrio chega em 2029.
> Nosso pedido é duplo: para a prefeitura, um **piloto de seis meses na Subprefeitura Sé, de 150 mil reais**, com a meta
> de cortar 30% dos chamados duplicados; e para investidores, **300 mil reais de pré-seed** para chegar lá.

## Fechamento — os três (4:50–5:00)

> **VigiaVia: cada buraco vira um relato, antes de virar um acidente.**

*Tela final: nomes completos, RMs, URL do MVP e repositório.*

---

## Falas por pessoa (para ler na hora de gravar)

**Deivison** — blocos 1, 2 e 6 + fechamento. **Eduardo** — bloco 3 + fechamento. **Wesley** — blocos 4 e 5 + fechamento.
Gravem cada bloco como um arquivo separado; errou, repete o bloco inteiro (eu escolho a melhor tomada e corto na edição).
