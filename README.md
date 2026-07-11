<p align="center">
  <img src="logo-pytstop.png" width="512" alt="PytStop">
</p>

# PytStop -- Tech Challenge Fase 3

<p align="center">
  <a href="https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/workflows/ci.yml"><img src="https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/workflows/cd.yml"><img src="https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/workflows/cd.yml/badge.svg" alt="CD"></a>
  <img src="https://img.shields.io/badge/coverage-%E2%89%A595%25-brightgreen" alt="coverage >= 95%">
  <img src="https://img.shields.io/badge/python-3.14%2B-blue" alt="Python 3.14+">
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <img src="https://img.shields.io/badge/mypy-checked-2a6db2" alt="mypy checked">
  <img src="https://img.shields.io/badge/architecture-Clean%20%C2%B7%20import--linter-success" alt="Clean Architecture (import-linter)">
</p>

Sistema de gestão de ordens de serviço de uma oficina mecânica de médio porte (clientes, veículos, OS, estoque, orçamentos), construído com Domain-Driven Design na fase 1, evoluído na fase 2 para Clean Architecture com Kubernetes e CI/CD, e levado à nuvem AWS na fase 3: API Gateway + autenticação serverless na borda, cluster EKS, banco gerenciado RDS e observabilidade completa.

## Este repositório entre os quatro

A fase 3 exige o projeto em repositórios separados, cada um com CI/CD próprio ([ADR-033](docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)). **Este repo (`postech-sw-arch-p3`) é a aplicação**: o monolito FastAPI (Clean Architecture), os manifests Kubernetes de [`k8s/`](k8s/README.md) — incluindo o overlay EKS — e o pipeline que builda a imagem e faz o deploy no cluster.

| Repositório | Conteúdo | Terraform |
|---|---|---|
| **postech-sw-arch-p3** (este) | Aplicação, manifests `k8s/` + overlay EKS, CI/CD do app | — |
| [postech-sw-arch-p3-lambda](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda) | Lambda de autenticação por CPF + Lambda authorizer + template SAM (emulação local) | API Gateway (HTTP API) + Lambdas ([ADR-027](docs/arquitetura/adr/fase3/027-api-gateway-aws.md), [ADR-028](docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md)) |
| [postech-sw-arch-p3-infra-k8s](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-k8s) | Infraestrutura Kubernetes | Cluster EKS + node group + metrics-server ([ADR-030](docs/arquitetura/adr/fase3/030-cluster-kubernetes-eks.md)) |
| [postech-sw-arch-p3-infra-db](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-db) | Infraestrutura de banco | RDS PostgreSQL 16 ([ADR-031](docs/arquitetura/adr/fase3/031-banco-gerenciado-rds.md)) |
| [postech-sw-arch-p3-docs](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs) | Documentação operacional (runbook `aws-academy-setup.md`, pesquisas da fase) | — |

**Objetivos da fase 3** ([enunciado](docs/requisitos/fase3/desafio-tech-fase-3.md) · [gap analysis](docs/requisitos/fase3/gap-analysis-fase-3.md)):

- **Autenticação serverless por CPF** (RF-025): Lambda Python valida o CPF, consulta o cliente no RDS e emite JWT compatível com o validador do app ([ADR-028](docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md));
- **API Gateway na frente das rotas** (RF-026): Amazon API Gateway (HTTP API) com Lambda authorizer nas rotas sensíveis ([ADR-027](docs/arquitetura/adr/fase3/027-api-gateway-aws.md));
- **Cluster Kubernetes escalável na nuvem** (RNF-025/026): Amazon EKS via Terraform em repo próprio, kind mantido como alvo local ([ADR-030](docs/arquitetura/adr/fase3/030-cluster-kubernetes-eks.md));
- **Banco gerenciado com justificativa formal e ER** (RNF-027): Amazon RDS for PostgreSQL 16 ([ADR-031](docs/arquitetura/adr/fase3/031-banco-gerenciado-rds.md), ER na [RFC-003 §2](docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md));
- **Dashboards e monitoramento** (RF-027): Prometheus + Grafana + Loki + Jaeger, com métricas de negócio, alertas e logs correlacionados ([ADR-032](docs/arquitetura/adr/fase3/032-monitoramento-grafana-loki.md));
- **CI/CD multi-repo com deploy homolog/produção** (RNF-025): GitHub Actions por repo, push em `homolog` → homologação, push em `main` → produção ([ADR-033](docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)).

O desenho integrado está na [RFC-003](docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md); a nuvem-alvo (AWS Academy Learner Lab) e suas restrições, no [ADR-026](docs/arquitetura/adr/fase3/026-cloud-alvo-aws-academy.md).

## Arquitetura da fase 3

Visão de nuvem integrada — borda serverless, cluster, banco e monitoramento — com a marcação de qual repositório provisiona o quê:

<!-- fonte: RFC-003 §4 — manter em sincronia -->
```mermaid
flowchart TB
    cliente(["Cliente da oficina<br/>(autentica por CPF)"])
    interno(["Usuário interno<br/>(admin / atendente / mecânico)"])

    subgraph aws["AWS us-east-1 — conta AWS Academy (ADR-026)"]
        subgraph borda["Borda serverless — Terraform em p3-lambda"]
            apigw["Amazon API Gateway<br/>HTTP API (ADR-027)"]
            lambda_auth["Lambda de autenticação<br/>python3.13 (ADR-028)"]
            authorizer["Lambda authorizer<br/>valida JWT HS256 (ADR-027)"]
        end
        subgraph eks["Amazon EKS (ADR-030) — Terraform em p3-infra-k8s · manifests k8s/ neste repo"]
            app["PytStop API — Deployment<br/>Clean Architecture + HPA<br/>(valida JWT também — defense in depth)"]
            relay["Relay de eventos<br/>outbox → SMTP (ADR-022)"]
            redis["Redis — rate limiter"]
            mailpit["Mailpit — SMTP de demo"]
            subgraph mon["Monitoramento (ADR-032)"]
                prometheus["Prometheus<br/>métricas de API, relay e cluster"]
                grafana["Grafana<br/>dashboards + alertas"]
                loki["Loki + Promtail<br/>logs JSON agregados"]
                ksm["kube-state-metrics<br/>CPU e memória"]
                jaeger["Jaeger<br/>traces OTel"]
            end
        end
        subgraph db["Terraform em p3-infra-db"]
            rds[("RDS PostgreSQL 16<br/>db.t3.micro single-AZ (ADR-031)")]
        end
    end

    cliente -->|"POST rota de autenticação (CPF)"| apigw
    cliente -->|"rotas protegidas + Bearer"| apigw
    interno -->|"login interno + rotas + Bearer"| apigw
    apigw -->|"invoca"| lambda_auth
    apigw -.->|"consulta autorização"| authorizer
    apigw -->|"roteia por prefixo"| app
    lambda_auth -->|"consulta cliente<br/>(documento_hash, ativo) — só leitura"| rds
    app -->|"SQL via DATABASE_URL"| rds
    app -->|"grava outbox + NOTIFY<br/>na mesma transação"| rds
    relay -->|"LISTEN/NOTIFY + claim outbox"| rds
    relay -->|"SMTP"| mailpit
    app -.->|"rate limit"| redis
    app -.->|"traces OTLP"| jaeger
    prometheus -.->|"scrape /metrics"| app
    prometheus -.->|"scrape"| relay
    prometheus -.->|"scrape"| ksm
    loki -.->|"coleta logs dos pods"| app
    grafana -.->|"consulta"| prometheus
    grafana -.->|"consulta"| loki
```

No ambiente local a caixa `borda` é substituída por `sam local start-api` (repo p3-lambda, só a rota de autenticação) e o EKS pelo kind — o resto do diagrama é idêntico. A tabela de paridade cloud × local, componente a componente, está na [RFC-003 §3](docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md).

A aplicação é um monolito modular: cada contexto delimitado segue as camadas da Clean Architecture (Entidades, Casos de Uso, Adaptadores de Interface, Frameworks & Drivers), mapeadas sobre as pastas `dominio/`, `aplicacao/`, `interfaces/` e `infraestrutura/` de cada módulo. A regra de dependência é verificada em todo build por `make lint-arch` (import-linter). Convenção de idioma híbrida ([ADR-009](docs/arquitetura/adr/009-decisao-de-idioma.md)): termos de negócio em português, padrões técnicos em inglês.

### Contextos Delimitados

| Contexto | Classificação | Descrição |
|---|---|---|
| Ordem de Serviço | Principal | Ciclo de vida da OS, orçamentos, máquina de estados |
| Cliente + Veículo | Suporte | Cadastro de clientes e veículos vinculados |
| Catálogo de Serviços | Suporte | Serviços oferecidos pela oficina |
| Estoque | Principal | Peças e insumos com controle de quantidade |
| Autenticação | Genérico | JWT, controle de acesso por papel |

## Execução local (docker-compose)

O desenvolvimento é **100% local** ([ADR-026](docs/arquitetura/adr/fase3/026-cloud-alvo-aws-academy.md)) — a AWS entra só em janelas de validação e demo.

> **Setup do zero?** Guias passo a passo por plataforma:
> [**Windows**](docs/setup/windows.md) - [**macOS**](docs/setup/macos.md) - [**Linux**](docs/setup/linux.md)

Pré-requisitos para quem já tem o ambiente pronto: Python 3.14+ (exigido pelo `pyproject.toml`), [uv](https://docs.astral.sh/uv/) ([ADR-014](docs/arquitetura/adr/014-gerenciador-pacotes-uv.md)), Docker 24+ com Compose v2 e Git.

```bash
git clone https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3.git
cd postech-sw-arch-p3
make reset-db                          # postgres + backend + mailpit + UI + seed completo
open http://localhost:8080/login       # atalhos Admin / Atendente / Mecanico
```

`make reset-db` derruba qualquer stack anterior, apaga o volume do postgres,
rebuilda imagens, aguarda o backend ficar saudável (healthcheck em
`/api/v1/saude`) e popula usuários + dados de demo (7 clientes, 10 veículos,
8 serviços, 14 itens, 8 OS em estados variados). **Apaga todos os dados do DB
local.** Para subir sem reset: `make up`. Derrubar tudo: `make down`. Após
`git pull`, prefira `make rebuild`.

Antes de cada push, rode o gate local espelho da CI (obrigatório enquanto a
cota do Actions estiver esgotada — [ADR-033](docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)):

```bash
make check    # lint + lint-arch + typecheck + security + testes (gate de 95%)
```

### URLs

| Serviço | URL |
|---|---|
| UI NiceGUI | http://localhost:8080 |
| Backend Swagger | http://localhost:8000/docs |
| Health probe | http://localhost:8000/api/v1/saude |
| Mailpit (caixa de e-mails da demo) | http://localhost:8025 |
| Jaeger UI (só com `--profile otel`) | http://localhost:16686 |

### Credenciais seed (dev-only -- abertas por design)

| Papel | E-mail | Senha |
|---|---|---|
| admin | `admin@pytstop.dev` | `admin-dev-pass-2026` |
| atendente | `atendente@pytstop.dev` | `atendente-dev-pass-2026` |
| mecanico | `mecanico@pytstop.dev` | `mecanico-dev-pass-2026` |

Na tela `/login`, os atalhos `ADMIN` / `ATENDENTE` / `MECANICO` logam
automaticamente. Pares **(placa, CPF/CNPJ)** das OS do seed:
[`ui/seed-users.md`](ui/seed-users.md).

## Deploy em Kubernetes local (kind)

Caminho recomendado — ciclo completo local, o mesmo que o CD executa:

```bash
make cd-local    # terraform apply + build da imagem + kind load + metrics-server + manifests + rollout + smoke
make k8s-down    # terraform destroy — remove cluster, banco e app
```

Pré-requisitos: [Terraform >= 1.7](https://developer.hashicorp.com/terraform/install), [kind](https://kind.sigs.k8s.io/) e kubectl, além do Docker (no Colima, reserve 4 GiB: `colima start --memory 4`).

O cluster sobe a aplicação **e a stack de monitoramento completa** ([ADR-032](docs/arquitetura/adr/fase3/032-monitoramento-grafana-loki.md)): Grafana (dashboards de negócio e plataforma + alertas provisionados), Loki + Promtail (logs JSON agregados), Prometheus + kube-state-metrics (métricas) e Jaeger (traces). Acesso por port-forward:

```bash
kubectl --context kind-pytstop -n pytstop port-forward svc/pytstop-ui 8080:8080     # UI NiceGUI: http://localhost:8080/login
kubectl --context kind-pytstop -n pytstop port-forward svc/pytstop-api 18000:8000   # Swagger: http://localhost:18000/docs
kubectl --context kind-pytstop -n pytstop port-forward svc/grafana 3000:3000        # Grafana: dashboards, logs (Loki) e alertas
kubectl --context kind-pytstop -n pytstop port-forward svc/prometheus 9090:9090     # Prometheus UI
kubectl --context kind-pytstop -n pytstop port-forward svc/jaeger 16686:16686       # Jaeger UI (traces)
kubectl --context kind-pytstop -n pytstop port-forward svc/mailpit 8025:8025        # Mailpit UI
```

Passo a passo manual, portas completas (inclui Loki 3100), validação do HPA sob carga, dashboards e correlação de logs por `request_id`: [`k8s/README.md`](k8s/README.md). Admin de demo do cluster (seed roda no Job `pytstop-migrate` durante o deploy): `admin@pytstop.dev` / `pytstop-admin-demo-2026` ([`k8s/secret.yaml`](k8s/secret.yaml)).

## Deploy na nuvem (EKS)

O alvo cloud usa os **mesmos manifests base** de `k8s/` com o overlay kustomize [`k8s/overlays/eks/`](k8s/overlays/eks/kustomization.yaml) ([ADR-030](docs/arquitetura/adr/fase3/030-cluster-kubernetes-eks.md)): imagens via GHCR (as mesmas que o CI publica por SHA), API exposta por Service `LoadBalancer` (endpoint que o API Gateway consome), `DATABASE_URL` apontando para o RDS via Secret `postgres-credentials` e **sem** metrics-server local (no EKS ele vem do provisionamento do cluster). Render local:

```bash
kubectl kustomize --load-restrictor=LoadRestrictionsNone k8s/overlays/eks
```

**Ordem de deploy multi-repo** ([ADR-033](docs/arquitetura/adr/fase3/033-cicd-multi-repo.md) — documentada, o gatilho entre repos é manual):

```
1. p3-infra-db    →  RDS no ar (endpoint + credenciais)
2. p3-infra-k8s   →  EKS no ar (kubeconfig)
3. p3-lambda      →  gateway + Lambdas (a function precisa do endpoint do banco)
4. p3 (este repo) →  migração + deploy da aplicação no EKS (cd.yml, job deploy-eks)
```

As credenciais AWS Academy são rotativas (~4h por sessão): os GitHub Secrets são re-gravados a cada *Start Lab* e o `terraform destroy` pós-demo é obrigatório — runbook `aws-academy-setup.md` no repo [p3-docs](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs).

## CI/CD

Padrão da fase 3 ([ADR-033](docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)): deploy automático por branch — push em **`homolog`** implanta no ambiente **homologação**; push em **`main`**, em **produção**. Main protegida, PRs obrigatórios.

| Workflow | Trigger | O que faz |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | PRs e push na main | lint (ruff + format), contratos de camadas (import-linter), mypy, bandit (`src ui relay scripts`), testes com gate de cobertura de 95% (src e ui), SBOM CycloneDX |
| [`security.yml`](.github/workflows/security.yml) | PRs, push na main, semanal | pip-audit (CVE em deps de runtime), gitleaks (segredos na árvore), trivy (CVE na imagem, HIGH/CRITICAL com `.trivyignore`) |
| CodeQL | PRs e push na main | SAST via **default setup** do GitHub (`Analyze (python)`); localmente `make codeql-quality` é o gate autoritativo (parte do `make all`) |
| [`cd.yml`](.github/workflows/cd.yml) | push em `main`/`homolog` + `workflow_dispatch` | build e push das imagens no GHCR (tag por SHA) → deploy em cluster kind efêmero no runner (validação sem custo) **e**, com os secrets AWS presentes, deploy no EKS via overlay `k8s/overlays/eks` no ambiente da branch (`homologacao`/`producao`) |
| [`full-test-ci.yml`](.github/workflows/full-test-ci.yml) | PRs + nightly | E2E concorrente contra a stack compose completa (journeys + matriz RBAC + DAST OWASP ZAP) |

Atualização de dependências automatizada por [Dependabot](.github/dependabot.yml) (uv, github-actions, docker), semanal.

> ⚠️ **Cota do GitHub Actions esgotada** (gap analysis §5): os pipelines estão commitados e corretos, mas não executáveis até a renovação da cota. O gate local espelho é obrigatório antes de cada push: `make check` (CI) e `make cd-local` (CD). Quando a cota renovar, o CI volta a ser o gate canônico sem mudança nos workflows.

## API

Documentação interativa no Swagger UI: `http://localhost:8000/docs` no compose, `http://localhost:18000/docs` via port-forward do cluster (na nuvem, o `/docs` responde no endpoint do LoadBalancer/gateway).

| Grupo | Prefixo | Operações |
|---|---|---|
| Clientes | /api/v1/clientes | CRUD + veículos + LGPD (dados pessoais, consentimento) |
| Serviços | /api/v1/servicos | CRUD catálogo |
| Estoque | /api/v1/estoque | CRUD + ajuste de quantidade |
| Ordens de Serviço | /api/v1/ordens-de-servico | Criação com serviços e peças, listagem ordenada por prioridade, ciclo completo da OS |
| Autenticação | /api/v1/autenticacao | Login interno, registro, refresh, logout (a autenticação de **clientes por CPF** entra pela borda serverless — [ADR-028](docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md)) |
| Público | /api/v1/acompanhamento · /api/v1/publico/.../decisao-orcamento | Acompanhamento por placa + documento e decisão externa de orçamento via assinatura HMAC |
| Admin / Outbox | /api/v1/admin/outbox | Operação da Transactional Outbox/DLQ, role `admin` |
| Saúde | /api/v1/saude | Health check (probes do Kubernetes) |

## Status e pendências

| Item | Status |
|---|---|
| Documentação de arquitetura (ADRs 026–033, RFC-003, gap analysis) | ✅ completa |
| Manifests k8s + stack de monitoramento no kind | ✅ no ar localmente (`make cd-local`) |
| Overlay EKS + pipeline homolog/produção | ✅ commitados ([`k8s/overlays/eks/`](k8s/overlays/eks/kustomization.yaml), [`cd.yml`](.github/workflows/cd.yml)) |
| Execução dos pipelines no GitHub Actions | ⏳ aguardando renovação da **cota do Actions** (gate local espelho em vigor) |
| Provisionamento EKS/RDS/gateway na AWS | ⏳ aguardando **credenciais AWS Academy** (sessões do Learner Lab; runbook no p3-docs) |
| Vídeo de demonstração e PDF da entrega | 📅 planejados para a fase 5 do cronograma interno |

## Desenvolvimento

| Tópico | Onde ler |
|---|---|
| Setup do zero (instalar uv, Docker, etc.) | [`docs/setup/`](docs/setup/) (Windows / macOS / Linux) |
| Loop de dev rápido (uvicorn hot-reload), checks locais, atualizar deps | [`docs/desenvolvimento.md`](docs/desenvolvimento.md) |
| Troubleshooting Docker (socket, Compose v2) e conflito uv/venv | [`docs/setup/troubleshooting.md`](docs/setup/troubleshooting.md) |
| Debugging do dev loop (Colima, JWT_SECRET, 500s comuns) | [`docs/debugging-guide.md`](docs/debugging-guide.md) |
| Manifests Kubernetes, monitoramento e validação do HPA | [`k8s/README.md`](k8s/README.md) |
| Terraform local do kind (recursos, variáveis, troubleshooting) | [`infra/README.md`](infra/README.md) |
| UI NiceGUI (simulação da API) | [`ui/README.md`](ui/README.md) |
| Worktrees paralelos (rodar 2+ branches sem conflito de portas) | [`docs/setup/worktrees-paralelos.md`](docs/setup/worktrees-paralelos.md) |

## UI de Simulação

Front em Python puro (NiceGUI) para testes manuais integrados da API — imagem própria (`ui/Dockerfile`). Roda no cluster (Deployment `pytstop-ui`, consome a API pelo Service interno `pytstop-api:8000`) e localmente via compose (`make up` → `http://localhost:8080`). Coexiste com o Swagger UI (`/docs`): Swagger é a referência crua da API, a UI de simulação é o front integrado. Guia completo: [`ui/README.md`](ui/README.md).

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| DATABASE_URL | URL de conexão PostgreSQL (tem precedência); no EKS vem do Secret `postgres-credentials` com o endpoint do RDS | postgresql://pytstop:pytstop@postgres:5432/pytstop |
| POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_HOST / POSTGRES_PORT | Fallback de montagem da URL só em dev/test quando `DATABASE_URL` está ausente (`src/main.py`) | -- / -- / -- / localhost / 5432 |
| JWT_SECRET | Chave secreta para tokens JWT (>= 32 bytes); **compartilhada com a Lambda de autenticação** ([ADR-028](docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md)) | change-this-in-production |
| JWT_EXPIRATION_MINUTES | Tempo de expiração do access token | 30 |
| JWT_REFRESH_EXPIRATION_MINUTES | Tempo de expiração do refresh token | 10080 (7 dias) |
| ENCRYPTION_KEY | Chave Fernet da PII em repouso (estável entre réplicas) | -- |
| ENVIRONMENT | Ambiente (development/production) | development |
| CORS_ORIGINS | Origens permitidas para CORS | http://localhost:3000 |
| RATE_LIMIT | Limite padrão do rate limiter, notação do pacote `limits` | 60/minute |
| TRUSTED_PROXIES | Proxies confiáveis para ler o `X-Forwarded-For` no rate-limit por IP real; vazio = XFF ignorado | vazio |
| RUN_MIGRATIONS_ON_STARTUP | Executar migrations ao iniciar o app | false (**false** no cluster — o Job `pytstop-migrate` é o dono da migração) |
| RUN_SEED_ON_STARTUP | Criar admin inicial no boot (best-effort) | false (**false** no cluster — seed roda no Job de migração) |
| SMTP_HOST / SMTP_PORT / SMTP_FROM | Servidor SMTP das notificações de status | mailpit / 1025 / oficina@pytstop.local |
| ORCAMENTO_WEBHOOK_TOKEN | Token do canal externo de decisão de orçamento | valor de demo no compose e no cluster |
| OTEL_ENABLED | Liga a instrumentação OpenTelemetry (traces) | false (true no cluster de demo) |
| OTEL_EXPORTER_OTLP_ENDPOINT | Endpoint OTLP/gRPC do backend de traces | http://jaeger:4317 |
| API_METRICS_ENABLED | Liga o `/metrics` Prometheus da API ([ADR-032](docs/arquitetura/adr/fase3/032-monitoramento-grafana-loki.md)) | false (true no cluster) |
| RATE_LIMIT_STORAGE_URI | Store compartilhado do rate limiter sob HPA | memory:// local / redis://redis:6379 no cluster |
| OUTBOX_POLL_SEGUNDOS / OUTBOX_LOTE / OUTBOX_LEASE_SEGUNDOS | Poll de segurança, lote e lease do relay da Transactional Outbox | 5 / 10 / 60 |
| RELAY_HEARTBEAT | Caminho do arquivo de heartbeat do relay (liveness) | /tmp/relay-heartbeat |
| RELAY_METRICS_ENABLED / RELAY_METRICS_PORT | Liga o `/metrics` do relay para o Prometheus | false / 9100 (true no cluster) |
| DB_POOL_SIZE / DB_MAX_OVERFLOW | Pool de conexões por réplica, dimensionado para o pior caso do HPA | 5 / 10 |
| DB_POOL_RECYCLE | Reciclagem de conexões do pool, em segundos | 1800 (30 min) |
| BACKEND_URL | URL do backend consumida pela UI | http://localhost:8001 local / http://app:8000 docker |
| UI_PORT | Porta da UI NiceGUI | 8080 |

Mapa completo variável → ConfigMap/Secret no cluster: [`k8s/configmap.yaml`](k8s/configmap.yaml) / [`k8s/secret.yaml`](k8s/secret.yaml).

## Stack

- **Linguagem**: Python 3.14 (app) · Python 3.13 (Lambda, repo p3-lambda)
- **Framework**: FastAPI
- **Banco de dados**: PostgreSQL 16 — local em Docker/kind, **Amazon RDS** na nuvem
- **ORM**: SQLAlchemy 2.0 (mapeamento imperativo)
- **Autenticação**: JWT (HS256) — emissores app (usuários internos) e Lambda (clientes por CPF), mesmo segredo e validador
- **Borda serverless**: Amazon API Gateway (HTTP API) + AWS Lambda + Lambda authorizer (repo p3-lambda)
- **E-mail**: adapter SMTP + Mailpit (demo)
- **Mensageria/eventos**: Transactional Outbox + processo relay (LISTEN/NOTIFY)
- **Rate limiting**: slowapi com storage compartilhado em Redis (sob HPA)
- **Observabilidade**: Prometheus (métricas de API, relay e cluster) + Grafana (dashboards e alertas) + Loki/Promtail (logs) + Jaeger (traces OTel)
- **Testes**: pytest, testcontainers, polyfactory
- **Linting**: ruff, mypy (strict), import-linter, bandit
- **Containerização**: Docker, Docker Compose
- **Orquestração e IaC**: Kubernetes — kind (local) e **Amazon EKS** (nuvem, Terraform no repo p3-infra-k8s), HPA
- **CI/CD**: GitHub Actions + GHCR, deploy por branch (homolog/produção)

## Testes

```bash
make test           # unitarios com cobertura (95%+ obrigatorio; configurado em .coveragerc)
make test-coverage  # unitarios com relatorio terminal e coverage.xml para CI/Sonar
make test-integ     # integracao com testcontainers + PostgreSQL
make test-all       # tudo (unitarios + integracao + e2e)
make lint-arch      # contratos de camadas Clean (import-linter, ADR-015)
make check          # gate local completo (espelho da CI)
```

Gate de cobertura de 95% herdado da fase 2 e mantido na fase 3 ([ADR-033](docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)). Detalhes do workflow de dev: [`docs/desenvolvimento.md`](docs/desenvolvimento.md).

## Code review automatizado pelo Claude

O repositório tem um workflow que roda o [Claude Code Action](https://github.com/anthropics/claude-code-action) oficial (secret `CLAUDE_CODE_OAUTH_TOKEN`): **Claude On-Demand** ([`claude-on-demand.yml`](.github/workflows/claude-on-demand.yml)), acionado por comentário `@claude` em PR/issue, por **Run workflow** na aba Actions ou por `gh workflow run claude-on-demand.yml --ref <branch> --field prompt="..."`. Os defaults ficam em [`.github/actions/claude/action.yml`](.github/actions/claude/action.yml). O lookup do workflow é sempre na `main` (limitação do GitHub Actions); cada run consome créditos do plano do owner do token.

## Decisões de Arquitetura (ADRs e RFCs)

### Fase 3

| Artefato | Título | Status |
|---|---|---|
| [RFC-003](docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md) | API Gateway, autenticação serverless e observabilidade (desenho integrado) | Aceita |
| [ADR-026](docs/arquitetura/adr/fase3/026-cloud-alvo-aws-academy.md) | AWS via conta AWS Academy Learner Lab como nuvem-alvo | Aceita |
| [ADR-027](docs/arquitetura/adr/fase3/027-api-gateway-aws.md) | Amazon API Gateway (HTTP API) + Lambda authorizer | Aceita |
| [ADR-028](docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md) | Autenticação serverless de clientes por CPF (Lambda + JWT HS256) | Aceita |
| [ADR-029](docs/arquitetura/adr/fase3/029-emulacao-local-lambda.md) | Emulação local da Lambda (pytest + SAM CLI) | Aceita |
| [ADR-030](docs/arquitetura/adr/fase3/030-cluster-kubernetes-eks.md) | Amazon EKS como cluster Kubernetes da fase 3 | Aceita |
| [ADR-031](docs/arquitetura/adr/fase3/031-banco-gerenciado-rds.md) | Amazon RDS for PostgreSQL como banco gerenciado | Aceita |
| [ADR-032](docs/arquitetura/adr/fase3/032-monitoramento-grafana-loki.md) | Stack de monitoramento Prometheus + Grafana + Loki | Aceita |
| [ADR-033](docs/arquitetura/adr/fase3/033-cicd-multi-repo.md) | CI/CD multi-repo com GitHub Actions | Aceita |

**Fases anteriores**: ADRs 000–014 (fase 1) e RFC-001/RFC-002 + ADRs 015–025 (fase 2) em [`docs/arquitetura/`](docs/arquitetura/); entregas históricas em [`docs/entrega/`](docs/entrega/README.md).

## Documentação

| Artefato | Descrição |
|---|---|
| [Tech Challenge Fase 3](docs/requisitos/fase3/desafio-tech-fase-3.md) | Especificação original da fase |
| [Gap Analysis Fase 3](docs/requisitos/fase3/gap-analysis-fase-3.md) | Challenge × código herdado → RF-025–027, RNF-025–030, RN-021/022 e riscos |
| [RFC-003](docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md) | Desenho integrado da fase 3 (topologias, diagramas, deploy multi-repo, correlação) |
| [Glossário](docs/requisitos/glossario.md) | Linguagem Ubíqua -- termos de domínio |
| [Mapa de Contextos](docs/arquitetura/mapa-contextos.md) | 5 contextos delimitados com padrões de integração |
| [Modelo de Domínio](docs/arquitetura/modelo-dominio.md) | Diagramas de classes por agregado |
| Fases anteriores | Domain Storytelling, Event Storming e entregas das fases 1–2: [`docs/arquitetura/`](docs/arquitetura/) e [`docs/entrega/`](docs/entrega/README.md) |

## Equipe

| Nome | RM | Discord |
|---|---|---|
| Joao Amaral | RM373448 | joao_13997 |
| Allan Aurelio | RM372116 | all66_ |
| Carlos Silva | RM374191 | carlossilva156 |
| Guilherme Sousa | RM373609 | romen0 |
| Nicolas Gerbi | RM372644 | sethiiz_gerbi |

## Curso

- **FIAP Pos Tech** -- Arquitetura de Software (15SOAT)
- **Fase 3 do Tech Challenge** -- vale 60% da nota de todas as disciplinas da fase
