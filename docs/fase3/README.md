# Fase 3 — índice dos artefatos

> [↑ Raiz do projeto](../../README.md)

> **Versão**: 1.0 — 06/10/2026. Um só lugar para achar cada artefato pedido na fase 3 do Tech Challenge. O enunciado está transcrito em [`desafio-tech-fase-3.md`](../requisitos/fase3/desafio-tech-fase-3.md).

## Diagramas, modelo de dados, RFC e ADRs

| Artefato pedido | Onde está | O que mostra |
|---|---|---|
| Diagrama de componentes (nuvem, APIs, banco, monitoramento) | [RFC-003 §4](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md#4-diagrama-de-componentes) | Borda serverless (API Gateway, Lambda de autenticação e authorizer), EKS com a API, RDS e a stack de monitoramento, marcando qual repositório provisiona cada parte |
| Diagrama de sequência: autenticação por CPF | [RFC-003 §5.1](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md#51-autenticação-de-cliente-por-cpf-e-consumo-de-rota-protegida) | Validação do CPF (módulo 11), consulta por `documento_hash`, emissão do JWT e consumo de rota protegida pelo gateway, authorizer e VPC Link |
| Diagrama de sequência: abertura de ordem de serviço | [RFC-003 §5.2](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md#52-abertura-de-ordem-de-serviço) | Criação da OS numa transação e entrega de notificações por outbox e relay |
| Modelo de dados (ER) e explicação dos relacionamentos | [RFC-003 §2, Modelo de dados](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md#modelo-de-dados-er-atualizado) | ER atualizado (`clientes`, `consentimentos`, `ordens_de_servico` e demais) com a leitura direta da Lambda |
| Justificativa formal do banco | [ADR-031](../arquitetura/adr/fase3/031-banco-gerenciado-rds.md) | Por que PostgreSQL no RDS, com alternativas e consequências |
| RFC | [RFC-003](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md) | Desenho integrado da fase: nuvem, topologia local espelho, deploy multi-repo, correlação de logs e riscos |
| Topologia local espelho (kind e SAM) | [RFC-003 §3](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md#3-topologia-local-espelho) | O que o ambiente local reproduz da AWS e o que só existe na nuvem |
| Fluxo de deploy multi-repo | [RFC-003 §6](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md#6-fluxo-de-deploy-multi-repo-cicd) | Ordem RDS, EKS, app e Lambda no CD |
| Correlação de logs e traces | [RFC-003 §7](../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md#7-correlação-de-logs-e-traces) | `X-Request-ID` do gateway até os logs da API e da Lambda |

Os diagramas de componentes, as duas sequências e o ER também aparecem nos READMEs de cada repositório e na seção 7 do [documento de entrega](../entrega/fase3/entrega-fase-3.md); a RFC-003 é a fonte e as cópias seguem os mesmos blocos Mermaid.

## ADRs da fase 3

| ADR | Decisão |
|---|---|
| [026](../arquitetura/adr/fase3/026-cloud-alvo-aws-academy.md) | Cloud alvo: AWS pela conta AWS Academy Learner Lab |
| [027](../arquitetura/adr/fase3/027-api-gateway-aws.md) | API Gateway: Amazon API Gateway (HTTP API) |
| [028](../arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md) | Autenticação serverless de clientes por CPF (Lambda Python) |
| [029](../arquitetura/adr/fase3/029-emulacao-local-lambda.md) | Emulação local da Lambda (pytest e AWS SAM CLI) |
| [030](../arquitetura/adr/fase3/030-cluster-kubernetes-eks.md) | Amazon EKS como cluster Kubernetes |
| [031](../arquitetura/adr/fase3/031-banco-gerenciado-rds.md) | Amazon RDS for PostgreSQL como banco gerenciado |
| [032](../arquitetura/adr/fase3/032-monitoramento-grafana-loki.md) | Stack de monitoramento: Prometheus, Grafana e Loki |
| [033](../arquitetura/adr/fase3/033-cicd-multi-repo.md) | CI/CD multi-repo com GitHub Actions, com adendos sobre proteção da `main` e ambientes |

As decisões das fases anteriores (ADRs 001 a 025, RFC-001 e RFC-002, Event Storming e Domain Storytelling) seguem válidas; o índice delas está em [`docs/arquitetura/README.md`](../arquitetura/README.md).

## Repositórios, pipelines e deploy

| Repositório | Conteúdo | README |
|---|---|---|
| `postech-sw-arch-p3` | API e UI (FastAPI), manifests Kubernetes, monitoramento, CI/CD do app | [README](../../README.md) |
| `postech-sw-arch-p3-lambda` | Function de autenticação por CPF, API Gateway e authorizer (Terraform), emulação SAM | [README](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda/blob/main/README.md) |
| `postech-sw-arch-p3-infra-k8s` | Terraform do cluster EKS | [README](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-k8s/blob/main/README.md) |
| `postech-sw-arch-p3-infra-db` | Terraform do RDS PostgreSQL | [README](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-db/blob/main/README.md) |
| `postech-sw-arch-p3-docs` | Repositório de processo (planos e runbooks); não conta para o requisito dos quatro repositórios | [README](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/README.md) |

## Observabilidade

| Artefato | Onde está |
|---|---|
| Dashboards em JSON e cada painel documentado (RF-027, RNF-028) | [`docs/observabilidade/dashboards-grafana.md`](../observabilidade/dashboards-grafana.md) |
| JSON dos dashboards | [`k8s/grafana/dashboards/`](../../k8s/grafana/dashboards) |
| Regras de alerta e stack provisionada como código | [`k8s/grafana.yaml`](../../k8s/grafana.yaml) |
| Escolha da stack | [ADR-032](../arquitetura/adr/fase3/032-monitoramento-grafana-loki.md) |
| Capturas dos dashboards e dos alertas | [`docs/entrega/fase3/evidencias`](../entrega/fase3/evidencias) |

## Requisitos, qualidade e segurança

| Artefato | Onde está |
|---|---|
| Gap analysis: enunciado contra o código da fase 2 | [`gap-analysis-fase-3.md`](../requisitos/fase3/gap-analysis-fase-3.md) |
| Rastreabilidade RF, RNF e RN até a evidência | [documento de entrega, seção 6](../entrega/fase3/entrega-fase-3.md) |
| Scans de segurança (SAST, SCA, DAST, SBOM, imagem) | [`docs/seguranca/scan-fase-3.md`](../seguranca/scan-fase-3.md) |
| OpenAPI e collection Postman | [`openapi-fase3.json`](../entrega/fase3/openapi-fase3.json) e [`postman-collection-fase3.json`](../entrega/fase3/postman-collection-fase3.json) |

## Governança e entrega

| Artefato | Onde está |
|---|---|
| Disciplina de PR e proteção da `main` | [`docs/governanca/disciplina-de-pr.md`](../governanca/disciplina-de-pr.md) |
| Feedback do professor e como cada ponto foi tratado | [`feedback-professor.md`](../entrega/fase3/feedback-professor.md) |
| Documento de entrega (fonte do PDF) | [`entrega-fase-3.md`](../entrega/fase3/entrega-fase-3.md) |
| Roteiro do vídeo | [`roteiro-video.md`](../entrega/fase3/roteiro-video.md) |
| Vídeo de demonstração | [youtu.be/5eRnYug4E3Q](https://youtu.be/5eRnYug4E3Q) |
| PDF de entrega | [release `entrega-fase-3`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/releases/tag/entrega-fase-3) |

> [↑ Raiz do projeto](../../README.md)
