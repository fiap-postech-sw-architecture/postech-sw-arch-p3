# Dashboards e alertas do Grafana

> [↑ Raiz do projeto](../../README.md)

> **Versão**: 1.0 — 06/10/2026. Atende o requisito RF-027 (dashboards de negócio) e o RNF-028 (métricas de plataforma e alertas) da fase 3. Decisão de ferramenta: [ADR-032](../arquitetura/adr/fase3/032-monitoramento-grafana-loki.md).

Cada dashboard é um arquivo JSON versionado, importável direto no Grafana (*Dashboards → Import*). Cada painel traz uma descrição que aparece como dica no próprio Grafana e que está repetida neste documento.

## Onde estão e como sobem

| Item | Caminho |
|---|---|
| Dashboard de negócio | [`k8s/grafana/dashboards/pytstop-negocio.json`](../../k8s/grafana/dashboards/pytstop-negocio.json) |
| Dashboard de plataforma | [`k8s/grafana/dashboards/pytstop-plataforma.json`](../../k8s/grafana/dashboards/pytstop-plataforma.json) |
| ConfigMap aplicado no cluster | `grafana-dashboards` em [`k8s/grafana.yaml`](../../k8s/grafana.yaml), gerado dos JSON |
| Regras de alerta | ConfigMap `grafana-alerting` em `k8s/grafana.yaml` |
| Gerador do ConfigMap | [`scripts/grafana_dashboards.py`](../../scripts/grafana_dashboards.py) (`make grafana-sync`) |
| Teste de consistência | [`tests/unitarios/scripts/test_grafana_dashboards.py`](../../tests/unitarios/scripts/test_grafana_dashboards.py) |

Os JSON são a fonte única. O ConfigMap é gerado por `make grafana-sync`, de modo que `kubectl apply -f k8s/*.yaml` (cluster kind e CD) e o overlay do EKS continuam funcionando sem etapa extra. O teste falha se o ConfigMap divergir dos JSON, se um painel ficar sem descrição ou se um painel não estiver documentado neste arquivo.

O Grafana provisiona os dashboards na pasta *PytStop* pelo provider `grafana-dashboards-provider` e os datasources Prometheus, Loki e Jaeger com UIDs fixos. O acesso anônimo entra como *Viewer*; o usuário admin usa a senha de demonstração do Secret `grafana-admin`.

Para ver no cluster local (`make cd-local`):

```bash
kubectl --context kind-pytstop -n pytstop port-forward svc/grafana 3000:3000
# http://localhost:3000/d/pytstop-negocio    e    http://localhost:3000/d/pytstop-plataforma
```

## Dashboard PytStop — Negócio (`pytstop-negocio`)

Janela padrão de 24 horas, atualização a cada 30 segundos.

| # | Painel | Tipo | Consulta (PromQL) | Como ler |
|---|---|---|---|---|
| 1 | OS criadas (últimas 24h) | stat | `sum(increase(pytstop_os_criadas_total[24h]))` | Volume diário de ordens de serviço (RF-027). Fica em 0 em ambiente recém-criado ou sem tráfego. |
| 2 | NOC — status dos serviços | stat | `min by (job) (up{job=~"pytstop-.*\|kube-state-metrics"})` | Verde (OK) quando o Prometheus coleta o serviço, vermelho (FORA) quando não. Cobre API, relay e kube-state-metrics. |
| 3 | Volume de OS criadas (por hora) | série | `sum(increase(pytstop_os_criadas_total[1h]))` | Distribuição horária do volume de OS (RF-027). Mostra os picos de entrada de veículos. |
| 4 | Tempo médio de OS por status | série | `sum by (status) (rate(pytstop_os_duracao_status_segundos_sum[1h])) / sum by (status) (rate(pytstop_os_duracao_status_segundos_count[1h]))` | Segundos que a OS permanece em cada status (RF-027). Valor alto em `aguardando_aprovacao` indica gargalo na aprovação do orçamento. |
| 5 | Erros de integração (outbox, por hora) | série | `sum(increase(outbox_falha_total[1h]))` e `sum(increase(outbox_dead_total[1h]))` | Tentativas de entrega com falha e eventos que esgotaram as tentativas (RF-027). Qualquer *dead* dispara o alerta `pytstop-outbox-dead`. |
| 6 | Eventos na fila da outbox (dead = alerta) | série | `outbox_pendentes` e `outbox_dead` | Estado da fila transacional. Pendentes que só crescem indicam relay parado; *dead* acima de 0 exige intervenção. |

## Dashboard PytStop — Plataforma (`pytstop-plataforma`)

Janela padrão de 6 horas, atualização a cada 30 segundos.

| # | Painel | Tipo | Consulta (PromQL) | Como ler |
|---|---|---|---|---|
| 1 | Health da API (up) | stat | `min(up{job="pytstop-api"})` | OK quando o Prometheus coleta o `/metrics` da API. Base do alerta `pytstop-api-fora`. |
| 2 | Uptime da API (24h) | stat | `avg(avg_over_time(up{job="pytstop-api"}[24h]))` | Disponibilidade da API nas últimas 24 horas, em percentual. |
| 3 | Taxa de erro (5xx) | série | `sum(rate(http_request_duration_seconds_count{status=~"5.."}[5m])) / sum(rate(http_request_duration_seconds_count[5m]))` | Proporção de respostas 5xx sobre o total. Acima de 1% por 5 minutos dispara `pytstop-taxa-5xx`. |
| 4 | Latência por rota — p50 / p90 / p99 | série | `histogram_quantile(0.50 \| 0.90 \| 0.99, sum by (le, rota) (rate(http_request_duration_seconds_bucket[5m])))` | Latência por rota a partir do histograma. O p95 acima de 300 ms por 5 minutos dispara `pytstop-latencia-p95`. |
| 5 | CPU por pod (cores) | série | `sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="pytstop", container!=""}[5m]))` | CPU por pod via cAdvisor. Referência para o alerta de CPU acima de 80% do limite. |
| 6 | Memória por pod (working set) | série | `sum by (pod) (container_memory_working_set_bytes{namespace="pytstop", container!=""})` | Memória em uso por pod. Crescimento contínuo sugere vazamento; compare com o limite do deployment. |

## Regras de alerta (pasta *PytStop*)

Avaliadas a cada minuto; a notificação usa a política padrão do Grafana, sem canal externo, o que basta para a demonstração (ADR-032).

| UID | Condição | Janela | Severidade | Painel relacionado |
|---|---|---|---|---|
| `pytstop-cpu-pod-alta` | CPU do pod acima de 80% do limite | 10 min | warning | Plataforma, painel 5 |
| `pytstop-latencia-p95` | p95 da latência acima de 300 ms | 5 min | warning | Plataforma, painel 4 |
| `pytstop-taxa-5xx` | mais de 1% das respostas com 5xx | 5 min | critical | Plataforma, painel 3 |
| `pytstop-outbox-dead` | `max(outbox_dead) > 0` (falha no processamento de OS) | 1 min | critical | Negócio, painéis 5 e 6 |
| `pytstop-api-fora` | `min(up{job="pytstop-api"}) < 1` | 1 min | critical | Plataforma, painel 1 |

## De onde vêm as métricas

| Métrica | Tipo | Origem no código |
|---|---|---|
| `pytstop_os_criadas_total` | contador | [`src/compartilhado/infraestrutura/metrics.py`](../../src/compartilhado/infraestrutura/metrics.py), incrementado pelo listener de [`src/ordem_servico/infraestrutura/metrics.py`](../../src/ordem_servico/infraestrutura/metrics.py) a cada OS inserida |
| `pytstop_os_duracao_status_segundos` | histograma, label `status` | mesmo módulo; observa o tempo no status anterior a cada transição |
| `http_request_duration_seconds` | histograma, labels `method`, `rota`, `status` | `MetricasHTTPMiddleware`; `rota` é o template da rota, não o caminho bruto |
| `outbox_pendentes`, `outbox_dead` | *gauges* | [`relay/metrics.py`](../../relay/metrics.py), lidos da fila no banco |
| `outbox_falha_total`, `outbox_dead_total` | contadores | `relay/metrics.py`, incrementados pelo processador de eventos |
| `up` | *gauge* do Prometheus | jobs `pytstop-api`, `pytstop-relay`, `kube-state-metrics` em [`k8s/prometheus.yaml`](../../k8s/prometheus.yaml) |
| `container_*` | cAdvisor | job `kubelet-cadvisor` em `k8s/prometheus.yaml` |

## Evidências

Capturas dos dois dashboards e das regras de alerta, obtidas no cluster kind em 10/09/2026, estão na pasta [`docs/entrega/fase3/evidencias`](../entrega/fase3/evidencias): `b2a-grafana-negocio.png`, `b2b-grafana-plataforma.png` e `b2c-grafana-alertas.png`.

> [↑ Raiz do projeto](../../README.md)
