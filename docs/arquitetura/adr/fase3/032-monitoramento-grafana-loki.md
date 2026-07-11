# Stack de monitoramento Prometheus + Grafana + Loki

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

O Tech Challenge da fase 3 exige monitoramento e observabilidade completos: "integração com ferramentas como Datadog ou New Relic (**escolha livre**)", cobrindo latência das APIs, consumo de CPU/memória do Kubernetes, healthchecks/uptime, alertas para falhas no processamento de OS e logs estruturados JSON com correlação entre requisições; e dashboards com volume diário de OS, tempo médio por status e erros de integrações — ver [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md) e os requisitos RF-027, RNF-028 e RNF-029 no [gap analysis](../../../requisitos/fase3/gap-analysis-fase-3.md).

O estado herdado da fase 2 é uma base parcial:

- **Prometheus** já roda no cluster (`k8s/prometheus.yaml`), mas hoje coleta apenas as métricas do relay/outbox ([ADR-024](../fase2/024-metricas-prometheus.md)) — a API não expõe métricas próprias (gap RF-027);
- **OpenTelemetry + Jaeger** cobrem traces ([ADR-020](../fase2/020-observabilidade-opentelemetry.md)), mas com `OTEL_ENABLED` desligado por padrão;
- **Logs estruturados JSON** com scrub de PII e `X-Request-ID` propagado já existem no app (gap RNF-029) — mas não são agregados nem consultáveis em ferramenta alguma;
- Não há Grafana, não há coleta de CPU/memória do cluster, não há alertas.

O material da fase aponta duas rotas. O módulo **Monitoramento** é todo open source e auto-hospedado: Zabbix (Aulas 01–02), e Grafana + Loki + Promtail para logs (Aula 03), fechando com "juntamente com as ferramentas Zabbix e Prometheus, os logs [...] completam toda uma stack sobre monitoramento". O módulo **Monitoramento-Avançado** usa **Datadog** (Aulas 02–06) e **New Relic** (Aulas 07–12) como veículo didático de APM, alertas, dashboards e SRE — mas reconhece explicitamente a alternativa aberta: "Ainda que tenhamos ferramentas open source como Grafana, Prometheus e Zabbix, muitas empresas acabam adotando a prática de All-in-One" (Aula 04).

**Qual stack de monitoramento cobre RF-027, RNF-028 e RNF-029 — e como ela aproveita o que já existe?**

## Decisão

Adotar uma **stack aberta auto-hospedada no cluster**, evoluindo a base da fase 2 em vez de trocá-la:

- **Métricas de aplicação**: o Prometheus existente (`k8s/prometheus.yaml`) passa a raspar também a **API instrumentada** — latência p50/p90/p99 por endpoint e **métricas de negócio**: volume diário de OS, tempo médio por status e erros de integração (RF-027). O formato de tabela por serviço com "taxa de requests, taxa de erro, latência p50, p90 e p99" vem direto do material (Monitoramento-Avançado, Aula 06).
- **Métricas de cluster**: **kube-state-metrics** (estado dos objetos) + scrape do **cAdvisor/kubelet** pelo Prometheus para uso de CPU/memória de pods e nodes (RNF-028), correlacionáveis com as métricas de aplicação — a correlação infra × aplicação que as Aulas 04 e 09 de Monitoramento-Avançado enfatizam. O metrics-server (API `metrics.k8s.io`, consumida pelo HPA e `kubectl top`) é instalado pelo provisionamento do cluster ([ADR-030](030-cluster-kubernetes-eks.md)) e não é fonte do Prometheus.
- **Dashboards**: **Grafana** como camada única de visualização, com dashboards **JSON versionados no git** — a prática de exportação/versionamento ensinada no material (Monitoramento-Avançado, Aulas 06 e 11) — cobrindo os três painéis exigidos pelo RF-027 e um painel de correlação aplicação × infra.
- **Logs**: **Loki + Promtail** agregando os logs JSON estruturados dos pods, consultáveis no Grafana com **correlação por `request_id`** — a arquitetura da Aula 03 do módulo Monitoramento (Loki na porta 3100, labels por job) adaptada de VMs para o cluster; o app já emite JSON estruturado com `X-Request-ID` propagado (RNF-029), então o gap é só a agregação e a propagação do id pela cadeia gateway → lambda → app.
- **Alertas**: **Grafana alerting** com regras baseadas em SLO, traduzindo os exemplos do material (Monitoramento-Avançado, Aulas 05 e 10) para o nosso contexto: CPU > 80% por 10 min; latência p95 > 300 ms por 5 min em endpoint crítico; taxa de erro > 1%; `/health` fora do ar; e **outbox dead** (falha no processamento de OS — RNF-028), usando as métricas do relay que já existem ([ADR-024](../fase2/024-metricas-prometheus.md)).
- **Traces**: **Jaeger mantido** como está ([ADR-020](../fase2/020-observabilidade-opentelemetry.md)); `OTEL_ENABLED` passa a **ligado por padrão nos ambientes de demo**, para que "logs e traces em execução" (entregável do vídeo) sejam demonstráveis sem toggle manual.

## Alternativas Consideradas

* Stack aberta auto-hospedada (Prometheus + Grafana + Loki + Jaeger)
* Datadog
* New Relic
* Zabbix
* Amazon CloudWatch

### Stack aberta auto-hospedada (Prometheus + Grafana + Loki + Jaeger)

* Bom, porque reaproveita tudo que já roda: Prometheus, Jaeger, logs JSON com request id, métricas do relay — o delta é instrumentar a API e adicionar Grafana/Loki/kube-state-metrics
* Bom, porque é exatamente a stack do módulo Monitoramento (Grafana + Loki + Promtail, Aula 03; Prometheus como coletor de métricas da stack) e a alternativa open source que o próprio módulo Monitoramento-Avançado reconhece (Aula 04)
* Bom, porque roda idêntica no kind local e no EKS — paridade local-first, custo zero, sem dependência de conta externa nem trial expirando no meio da avaliação
* Bom, porque dashboards e regras de alerta viram código versionado (JSON/ConfigMaps no git), a prática de rastreabilidade que o material recomenda (Monitoramento-Avançado, Aulas 06 e 10)
* Ruim, porque as técnicas de APM do módulo avançado (Timeboards, monitores, NRQL) precisam ser traduzidas para os equivalentes Grafana/Prometheus em vez de aplicadas literalmente — tradução que os fichamentos já mapeiam

### Datadog

* Bom, porque é o veículo didático de metade do módulo Monitoramento-Avançado (Aulas 02–06: APM, logs, infra, alertas, dashboards) e é citado nominalmente no challenge
* Bom, porque é all-in-one: métricas, traces, logs e alertas numa plataforma só, sem montar peças
* Ruim, porque é SaaS pago com trial limitado e agente proprietário — risco de expirar/custar durante a avaliação, contra o critério local-first e o budget Academy
* Ruim, porque o próprio material o apresenta como opção entre outras, reconhecendo a stack aberta como alternativa (Aula 04), e o challenge diz "escolha livre" — não há exigência a cumprir
* Ruim, porque nada dele roda no kind local: a paridade dev/demo se perde

### New Relic

* Bom, porque cobre a outra metade do módulo (Aulas 07–12: APM, Apdex, NRQL, dashboards, service maps) e também é citado no challenge
* Ruim, pelos mesmos motivos do Datadog: SaaS com free tier limitado, agente proprietário, zero paridade local — e as técnicas que o material ensina nele (dashboards por query, alertas por SLO) têm equivalente direto na stack aberta

### Zabbix

* Bom, porque domina dois terços do módulo Monitoramento (Aulas 01–02: server + front-end via Docker Compose, monitoramento de banco via ODBC com usuário de privilégios mínimos)
* Ruim, porque é forte em infraestrutura clássica (hosts, agents, ODBC) e duplicaria o papel do Prometheus já existente no cluster — duas ferramentas de métricas para o mesmo trabalho
* Ruim, porque não cobre logs nem traces — a própria Aula 03 do módulo o complementa com Grafana/Loki, que é onde esta decisão já está

### Amazon CloudWatch

* Bom, porque é nativo do EKS/RDS ([ADR-030](030-cluster-kubernetes-eks.md)/[ADR-031](031-banco-gerenciado-rds.md)) — coleta de métricas e logs sem instalar nada
* Ruim, porque prende o monitoramento à AWS: nada funciona no kind local, e a conta AWS Academy é efêmera (recursos destruídos pós-demo levariam dashboards e histórico junto)
* Ruim, porque não aparece no material de nenhum dos dois módulos da fase — custo de aprendizado sem lastro na avaliação

## Consequências

### Positivas

* RF-027, RNF-028 e RNF-029 cobertos com uma stack única, demonstrável no vídeo tanto local (kind) quanto no EKS — dashboards, alertas, logs correlacionados e traces ao vivo
* Evolução, não substituição: o investimento da fase 2 (Prometheus, Jaeger, logs estruturados, métricas do relay) é a fundação; nenhum componente é jogado fora
* Observabilidade como código: dashboards JSON, regras de alerta e scrape configs versionados — auditáveis no PR, reproduzíveis por `kubectl apply`/kustomize

### Negativas

* Mais componentes no cluster (Grafana, Loki, Promtail, kube-state-metrics) consomem recursos dos nodes — relevante no node group mínimo do EKS ([ADR-030](030-cluster-kubernetes-eks.md)) e no kind local
* Sem SaaS, não há alerting gerenciado com paging (PagerDuty etc.): os alertas do Grafana notificam por canais simples, suficiente para a demo, aquém de operação 24/7 real
* A correlação de `request_id` fim a fim (gateway → lambda → app) é detalhada no RFC-003 — o risco de correlação quebrada na borda é apontado no gap analysis (§5)

### Neutras

* Definições exatas de SLO/SLI (targets numéricos, error budget) e os thresholds finais dos alertas ficam para o documento de SLO/runbook, guiados pelos exemplos do material (Monitoramento-Avançado, Aulas 01, 05 e 10)
* Retenção de logs/métricas, storage do Loki e sizing do Prometheus são detalhes de implementação dos manifests, fora deste ADR

## Decisões Relacionadas

- [ADR-020](../fase2/020-observabilidade-opentelemetry.md): OpenTelemetry + Jaeger continuam como pilar de traces; muda apenas o default de `OTEL_ENABLED` nos ambientes de demo
- [ADR-024](../fase2/024-metricas-prometheus.md): as métricas do relay/outbox viram a base dos alertas de falha de processamento de OS (RNF-028)
- [ADR-022](../fase2/022-transactional-outbox-relay.md): o outbox cuja saúde os alertas passam a vigiar
- [ADR-030](030-cluster-kubernetes-eks.md): a stack roda dentro do cluster, nos dois alvos (kind e EKS)
- [ADR-033](033-cicd-multi-repo.md): dashboards e regras versionados entram no fluxo de PR/CI do repo principal

## Notas

* Fonte das evidências de material: fichamentos dos módulos Monitoramento (Aulas 01–03) e Monitoramento-Avançado (Aulas 01–12) da fase 3, em `postech-sw-arch-p3-docs/docs/superpowers/research/` (`monitoramento.md`, `monitoramento-avancado.md`); as citações "(Módulo, Aula NN)" referem-se ao material oficial da FIAP Pos Tech
* Requisitos formais: RF-027, RNF-028, RNF-029 ([gap-analysis-fase-3.md](../../../requisitos/fase3/gap-analysis-fase-3.md)); exigência original em [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md)
* Os exemplos de alerta citados (CPU > 80%/10 min; p95 > 300 ms/5 min; taxa de erro > 1%; `/health` em falha) são os do material (Monitoramento-Avançado, Aula 05), adaptados ao contexto do PytStop

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
