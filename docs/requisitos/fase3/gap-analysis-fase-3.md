# Gap Analysis — Tech Challenge Fase 3 × Código da Fase 2

> Origem dos requisitos: [desafio-tech-fase-3.md](desafio-tech-fase-3.md). IDs continuam a numeração
> das fases anteriores (últimos: RF-024, RNF-024, RN-020). Evidências levantadas sobre o snapshot
> do p2 importado neste repositório (`p2 @ de4d0c6`).

## 1. Tabela de gaps

| ID | Requisito (challenge) | Estado no p2 (evidência) | Gap | Ação na fase 3 |
|---|---|---|---|---|
| RF-025 | Function Serverless de autenticação: validar CPF, consultar existência e status do cliente, emitir JWT | Autenticação é serviço próprio no monólito: emissão HS256 em `src/autenticacao/infraestrutura/jwt_service.py:36-58`, login em `src/autenticacao/interfaces/router.py:38`; consulta de cliente por documento existe só como método interno `obter_por_documento` (`src/cliente_veiculo/dominio/repository.py:31`, impl. `infraestrutura/repository.py:69-73`, por `documento_hash`); cliente tem campo `_ativo` (`dominio/cliente.py:57`) | Não existe function serverless nem fluxo CPF→token | Lambda Python no repo `postech-sw-arch-p3-lambda` (ADR-028); emulação local (ADR-029) |
| RF-026 | API Gateway protegendo rotas sensíveis, com controle e roteamento | Não há gateway: rotas protegidas direto no app via `obter_usuario_atual` (`src/autenticacao/interfaces/middleware.py:28-72`) e RBAC `exigir_papel` (`interfaces/middleware.py:88-123`); rotas públicas em `src/compartilhado/interfaces/router_publico.py:54` | Gateway inexistente | Gateway conforme ADR-027, roteando app + lambda; rotas sensíveis exigem JWT emitido pela lambda (RN-021) |
| RF-027 | Dashboards: volume diário de OS, tempo médio por status, erros de integrações | Sem Grafana; Prometheus só coleta métricas do relay/outbox (`k8s/prometheus.yaml:19-26`, `relay/metrics.py:214-251`); API sem métricas próprias; endpoint `GET /metricas` de OS existe (`src/ordem_servico/interfaces/router.py`) mas não alimenta dashboard | Não há dashboards nem métricas de negócio expostas | Instrumentar API (métricas de negócio + latência) e construir dashboards (ADR-032) |
| RNF-025 | 4 repositórios separados, cada um com CI/CD e deploy automático (homolog/produção); main protegida; PRs obrigatórios | Monorepo p2 com 6 workflows (`.github/workflows/ci.yml`, `cd.yml`, `security.yml`, `full-test-ci.yml`, 2 Claude); CD faz deploy k8s local/cloud (`cd.yml:29-66`) | Segregação inexistente; CD não é multi-repo nem homolog/produção | Repos `p3`, `p3-lambda`, `p3-infra-k8s`, `p3-infra-db` com pipelines próprios (ADR-033); branch protection ao fim do bootstrap |
| RNF-026 | Terraform provisionando API Gateway, Function, banco gerenciado e cluster K8s na nuvem | Terraform atual: kind local (`infra/main.tf:7`, `infra/postgres.tf`), Azure AKS (`infra/azure-aks/main.tf:27`) e Azure VM (`infra/azure-vm/main.tf:131`) — nada AWS | IaC alvo errado (Azure/local) e acoplada ao monorepo | Terraform AWS Academy nos repos infra (ADR-026/030/031); `infra/` do snapshot é removido do p3 (§4) |
| RNF-027 | Banco de dados gerenciado + justificativa formal + diagrama ER | PostgreSQL 16 em StatefulSet no cluster (`infra/postgres.tf:33`); ER mermaid existe em `docs/arquitetura/rfc/rfc-001-design-do-sistema.md:104`; 8 migrações Alembic (`migrations/versions/001..008`) | Banco não é gerenciado; justificativa formal exigida não existe como documento próprio | RDS PostgreSQL via Terraform (`p3-infra-db`, ADR-031) com justificativa formal + ER atualizado |
| RNF-028 | Monitorar latência das APIs, CPU/memória do K8s, healthchecks/uptime, alertas de falha no processamento de OS | OTel traces (default OFF, `observability.py:90-94`) → Jaeger; probes liveness/readiness apontam ambos para `/api/v1/saude` (`k8s/deployment.yaml:63-75`); sem alertas; sem coleta de CPU/mem (sem kube-state-metrics/metrics de nó no Prometheus) | Latência, recursos K8s, uptime e alertas não monitorados | Stack de monitoramento do ADR-032 (coleta de latência, recursos, uptime, alertas de OS/outbox) |
| RNF-029 | Logs estruturados JSON com correlação entre requisições | Já implementado no app: structlog JSON (`logging.py:252`), scrub PII (`logging.py:106-158`), `X-Request-ID` propagado (`middleware.py:41-54`) | Parcial: correlação não atravessa gateway→lambda→app; logs não são agregados/consultáveis em ferramenta | Propagar correlation id na cadeia completa; agregação de logs (ADR-032) |
| RNF-030 | Documentação arquitetural completa: diagrama de componentes (visão nuvem/APIs/banco/monitoramento), diagramas de sequência (autenticação e abertura de OS), RFCs e ADRs | RFC-001 tem diagramas de componentes/ER da fase 1 (`docs/arquitetura/rfc/rfc-001-design-do-sistema.md:104`); RFC-002 cobre infra da fase 2; ADRs 000-025 existentes; nenhum diagrama de sequência de autenticação via gateway/lambda (fluxo não existia) | Visão de nuvem AWS e sequência CPF→JWT inexistentes | ADRs 026+ e RFC-003 com diagrama de componentes + diagramas de sequência exigidos |
| RN-021 | Token emitido pela function é o aceito pelas APIs protegidas | App valida tokens do próprio emissor (`jwt_service.py:60-75`, claims sub/email/papel/jti) | Dois emissores potenciais (lambda × app) | Emissor único/claims compatíveis + segredo compartilhado, decidido no ADR-028 |
| RN-022 | CPF inexistente ou cliente inativo não recebe token | Invariante de cliente ativo existe no domínio (`cliente.py:115-124`); nenhum fluxo liga CPF→autenticação | Regra nova | Implementar na lambda (consulta status via banco; ADR-028) |

Entregáveis que não são requisitos funcionais (README por repo com diagrama e link Swagger/Postman, vídeo ≤ 15min, PDF de submissão, acesso do `soat-architecture` aos 4 repos) são rastreados no plano de entrega (fase 5 da spec de bootstrap, repo `postech-sw-arch-p3-docs`). O narrativo do desafio cita "serverless para autenticação **e notificações**", mas os requisitos obrigatórios só exigem serverless na autenticação — as notificações continuam no relay/outbox herdado (registrado aqui para não se perder).

## 2. Autenticação: gateway + lambda × JWT próprio

O contexto `autenticacao` do p2 permanece (usuários internos: admin/atendente/mecânico, RBAC por papel). O challenge adiciona autenticação **de cliente** via CPF na borda. Consequências:

- Dois públicos distintos: usuários internos (login/senha, fluxo atual) e clientes (CPF→JWT via lambda). O desenho de convivência — emissor único vs dois emissores com o mesmo segredo, claims e papel `cliente` — é decisão do ADR-028.
- O acompanhamento público por placa+documento (`src/compartilhado/interfaces/router_publico.py:88`, rate 10/min) pode ser absorvido pelas rotas protegidas por token de cliente ou mantido; decisão no RFC-003.
- O segredo `JWT_SECRET` hoje vive em env/Secret K8s (`k8s/secret.yaml:13`); com a lambda, passa a ser segredo compartilhado entre app e function (Secrets Manager/SSM × env — ADR-026/028).

## 3. Segregação em repositórios

| Repo | Conteúdo | Origem |
|---|---|---|
| `postech-sw-arch-p3` | Aplicação (src/, tests/, k8s/ da app, Dockerfiles, migrações) | Snapshot do p2 |
| `postech-sw-arch-p3-lambda` | Function de autenticação + testes + empacotamento + pipeline | Novo |
| `postech-sw-arch-p3-infra-k8s` | Terraform do cluster (EKS) + recursos de cluster | Novo (substitui `infra/` kind/AKS) |
| `postech-sw-arch-p3-infra-db` | Terraform do banco gerenciado (RDS) | Novo (substitui `infra/postgres.tf`) |
| `postech-sw-arch-p3-docs` | Processo (specs, planos, fichamentos, runbooks) | Novo; fora dos 4 exigidos |

## 4. Destino dos componentes herdados do p2

| Componente | Evidência | Destino na fase 3 |
|---|---|---|
| `infra/` (kind local + Postgres StatefulSet) | `infra/main.tf:7`, `infra/postgres.tf` | **Manter** como ferramenta do dev-loop local (`make k8s-up` depende dele); provisionamento de nuvem migra para os repos infra |
| `infra/azure-aks/`, `infra/azure-vm/` + overlays `cloud`/`vm-k3s` + alvos make | `azure-aks/main.tf:27`, `azure-vm/main.tf:131` | **Removido** (commit 947fe17) — cloud da fase 3 é AWS (ADR-026); histórico preservado no p2 |
| `k8s/` (manifests da app: deployment, service, HPA, configmap, secret, overlays) | `k8s/deployment.yaml:5`, `k8s/hpa.yaml:10` | **Manter no p3** (deploy da app); overlay novo para EKS; overlays `vm-k3s`/`cloud` Azure removidos |
| `k8s/prometheus.yaml`, `jaeger.yaml`, `mailpit.yaml`, `redis.yaml`, `relay.yaml` | `k8s/*.yaml` | Manter; evoluir conforme ADR-032 (monitoramento) |
| `ui/` (NiceGUI dev) | Makefile `ui:` (`Makefile:180`) | Manter como ferramenta de dev/demo (sem mudança) |
| `relay/` (outbox → e-mail/webhook) | `relay/metrics.py` | Manter (alertas de falha de OS usam suas métricas — RNF-028) |
| Workflows Claude (`claude-*.yml`) | `.github/workflows/` | Manter no p3; não replicar nos satélites |

## 5. Riscos

- **AWS Academy**: LabRole fixo, sessões de ~4h, budget pequeno — EKS+RDS consomem budget rápido; mitigação: `terraform destroy` pós-demo (runbook) e paridade local completa (kind + compose + SAM) para desenvolvimento sem custo.
- **Cota GitHub Actions esgotada**: pipelines novos não validáveis no CI até renovar; mitigação: gate local espelho (`make check` + validações Terraform/lambda) obrigatório antes de push.
- **Emissor JWT duplicado** (lambda × app): risco de tokens incompatíveis — tratado como RN-021 no ADR-028.
- **Correlação fim-a-fim** (gateway→lambda→app): request id atual nasce no middleware do app (`middleware.py:41`); precisa aceitar id vindo do gateway sem quebrar o scrub de PII.
- **Cobertura > 95%** (`.coveragerc:50` já exige 95): lambda nova precisa nascer com testes para não rebaixar o padrão.
