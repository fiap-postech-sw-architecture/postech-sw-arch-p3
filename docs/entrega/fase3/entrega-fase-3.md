# Documento de Entrega — Tech Challenge Fase 3

> [↑ Raiz do projeto](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3) · [↑ Entrega Fase 3](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/tree/main/docs/entrega/fase3)

> **Versão**: 1.1 — setembro/2026 (1.0: julho/2026).

Documento de entrega da fase 3 do Tech Challenge da Pós-Graduação em Arquitetura de Software (FIAP). O conteúdo cobre os itens exigidos pelo enunciado da fase: identificação do grupo, links dos quatro repositórios (compartilhados com o avaliador), link do vídeo de demonstração, links das documentações, desenho da arquitetura e a confirmação do usuário `soat-architecture` como colaborador.

## Como ler este documento

Os repositórios são a fonte de verdade. A fase 3 segrega a solução em quatro repositórios com CI/CD próprio (mais um quinto de processo): aplicação em Kubernetes, function serverless de autenticação + API Gateway, Terraform do cluster EKS e Terraform do banco gerenciado RDS — papéis na seção 2. O desenho da arquitetura é Mermaid renderizado pelo GitHub, com fonte única na [RFC-003 §4](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md), replicada na seção 7. As decisões estão nas ADRs 026–033 e na RFC-003. A rastreabilidade requisito → evidência está na seção 6, com o estado operacional registrado (deploy AWS — seções 2 e 9).

---

## 1. Identificação do grupo

| Campo | Valor |
|---|---|
| Nome do grupo | PytStop |
| Turma | 15SOAT — Pós-Graduação em Arquitetura de Software (FIAP) |

### Participantes

| Nome | RM | Discord |
|---|---|---|
| João Amaral | RM373448 | joao_13997 |
| Allan Aurélio | RM372116 | all66_ |
| Carlos Silva | RM374191 | carlossilva156 |
| Guilherme Sousa | RM373609 | romen0 |
| Nicolas Gerbi | RM372644 | sethiiz_gerbi |

## 2. Links dos repositórios

Repositórios **públicos** no GitHub (organização `fiap-postech-sw-architecture`) desde 03/09/2026, por orientação da FIAP: a correção automatizada do Tech Challenge exige repositórios públicos (Adendo (e) do [ADR-033](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)). A visibilidade pública também liberou a proteção técnica da `main` exigida pelo enunciado e os minutos ilimitados do Actions. O usuário `soat-architecture` é adicionado como colaborador de leitura em todos os repositórios, como o enunciado pede (pendência 2, seção 9). São os quatro repositórios exigidos pelo enunciado, mais um quinto de processo:

| Repositório | Papel na fase 3 | URL |
|---|---|---|
| `postech-sw-arch-p3` | Aplicação principal executando em Kubernetes (snapshot evoluído do p2 — Clean Architecture, manifests `k8s/`, monitoramento) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3 |
| `postech-sw-arch-p3-lambda` | Function serverless de autenticação por CPF + API Gateway + Lambda authorizer (código Python e Terraform da borda) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda |
| `postech-sw-arch-p3-infra-k8s` | Infraestrutura Kubernetes: Terraform do cluster Amazon EKS (node group, add-ons) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-k8s |
| `postech-sw-arch-p3-infra-db` | Infraestrutura do banco gerenciado: Terraform do Amazon RDS for PostgreSQL | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-db |
| `postech-sw-arch-p3-docs` | Processo da fase (specs, planos, runbooks de operação AWS) — além dos 4 exigidos | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs |

Cada um dos quatro repositórios exigidos tem README com propósito, tecnologias, passos de execução e deploy, diagrama da arquitetura específica e pipelines `ci.yml` + `cd.yml` com deploy automático por branch. Em app e lambda, push em `homolog` vai para o ambiente de homologação e push em `main` vai para produção. Nos repos de infra (`infra-k8s`/`infra-db`), push em `homolog` roda só `terraform plan` (estágio de homologação de infra); o apply automático fica na `main`, porque um único Learner Lab não comporta infra duplicada (Adendo (b) do [ADR-033](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)). A proteção técnica da branch `main` está **ativa nos cinco repositórios** desde 03/09/2026: PR obrigatório, sem commit direto (administradores incluídos), checks de CI e Security obrigatórios onde existem. Ela era inviável enquanto os repositórios eram privados no plano free (HTTP 403 "Upgrade to GitHub Pro"); tornar os repositórios públicos na entrega foi a opção escolhida entre as registradas no [Adendo do ADR-033](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/033-cicd-multi-repo.md#adendo-2026-07-11--limitações-constatadas-e-decisões-complementares).

### Estado do CI/CD e gate local espelho

Os pipelines dos quatro repositórios **executam no GitHub Actions** desde 01/08/2026 — a cota da organização, esgotada em julho, renovou, e repositórios públicos têm minutos ilimitados. Runs verdes de referência: `p3` — [CI](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/runs/30712167211), [Security](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/runs/30712167219), [CD em `main` (produção)](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/runs/30712167204), [CD em `homolog` (homologação)](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/runs/30713618605), [full-test E2E](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/runs/30712167236); [`p3-lambda` CI](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda/actions/runs/30706272676); [`p3-infra-k8s` CI](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-k8s/actions/runs/30706274897); [`p3-infra-db` CI](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-db/actions/runs/30706273765). O gate local espelho ([RFC-003 §6](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md)) continua obrigatório antes de cada push, como pré-check do CI — resultado na HEAD de 2026-07-11, reconfirmado em 03/09/2026 no [PR #14](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/pull/14):

| Repo | Gate local | Resultado |
|---|---|---|
| `p3` (app) | `make check` (lint, import-linter, mypy, bandit, testes) | Verde — **1.834 testes**, cobertura **96,4%** (gate ≥ 95%) |
| `p3` (app) | `make test-integ` (integração com PostgreSQL real) | Verde — **162 testes** |
| `p3` (app) | `make full-test` (E2E da jornada completa, stack compose) | Verde — 1 passed |
| `p3-lambda` | `make gate` (lint, mypy strict, bandit, testes, `terraform validate`) | Verde — **34 testes** unitários (+3 de integração via `make test-integ`), cobertura **100%** |
| `p3-infra-k8s` | `make gate` (`terraform fmt -check` + `validate`) | Verde |
| `p3-infra-db` | `make gate` (`terraform fmt -check` + `validate`) | Verde |

**Links para deploys ativos**: sem link fixo (ambiente efêmero) — a evidência de deploy é o runbook + o vídeo; justificativa — a nuvem alvo é a conta AWS Academy Learner Lab, efêmera por design (sessões de ~4h, `terraform destroy` obrigatório pós-demo para preservar o budget — [ADR-026](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/026-cloud-alvo-aws-academy.md)). Cada README documenta como subir o ambiente em minutos; o runbook de sessão é o [`aws-academy-setup.md`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/runbooks/aws-academy-setup.md) (repo `p3-docs`).

## 3. Link do vídeo

Vídeo de até 15 minutos demonstrando autenticação com CPF, execução da pipeline CI/CD, deploy automatizado, consumo das APIs protegidas, dashboard de monitoramento ao vivo e logs/traces em execução, conforme o enunciado. Roteiro de gravação: [roteiro-video.md](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/roteiro-video.md).

| Recurso | URL |
|---|---|
| Vídeo de demonstração | _link será adicionado após a gravação_ <!-- VIDEO-LINK-FASE-3 --> |

> Preenchimento: substituir a linha acima (e o marcador `VIDEO-LINK-FASE-3`) pela URL do YouTube/Vimeo (público ou não listado) antes de gerar o PDF — pendência 1, seção 9.

## 4. Link da documentação

Toda a documentação versionada está nos repositórios — a de arquitetura e requisitos no `p3` (pasta `docs/`), a de processo e operação no `p3-docs`.

### 4.1 Índice geral

| Recurso | URL |
|---|---|
| Pasta `docs/` do repo principal (índice) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/tree/main/docs |
| Requisitos da fase 3 (enunciado transcrito) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/requisitos/fase3/desafio-tech-fase-3.md |
| Gap analysis — enunciado × código da fase 2 (RF-025–027, RNF-025–030, RN-021–022) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/requisitos/fase3/gap-analysis-fase-3.md |
| README do `p3` (app: arquitetura, execução local, kind, EKS, CI/CD) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/README.md |
| README do `p3-lambda` (function, gateway, emulação SAM, deploy Terraform) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda/blob/main/README.md |
| README do `p3-infra-k8s` (Terraform do EKS) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-k8s/blob/main/README.md |
| README do `p3-infra-db` (Terraform do RDS) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-db/blob/main/README.md |
| README do `p3-docs` (processo da fase) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/README.md |
| Runbook — sessão AWS Academy (Start Lab, credenciais rotativas, secrets) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/runbooks/aws-academy-setup.md |
| Runbook — próximas etapas (ordem de deploy multi-repo e fechamento) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/runbooks/proximas-etapas.md |

### 4.2 Decisões de arquitetura da fase 3

Critério adotado: decisões pontuais e permanentes (nuvem, banco, autenticação, gateway) viram ADRs — o formato que o projeto usa desde a fase 1 para decisão com alternativas e consequências. O RFC-003 é o design integrado que costura essas decisões (o enunciado cita RFC como exemplo de formato, e o conjunto ADR+RFC cobre as três decisões citadas: nuvem no ADR-026, banco no ADR-031, autenticação no ADR-028).

| Artefato | Decisão | URL |
|---|---|---|
| RFC-003 | API Gateway, autenticação serverless e observabilidade — topologia de nuvem, ER atualizado, diagrama de componentes, diagramas de sequência (autenticação por CPF e abertura de OS) e fluxo de deploy multi-repo | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md |
| ADR-026 | Cloud alvo da fase 3: AWS via conta AWS Academy Learner Lab | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/026-cloud-alvo-aws-academy.md |
| ADR-027 | API Gateway da fase 3: Amazon API Gateway (HTTP API) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/027-api-gateway-aws.md |
| ADR-028 | Autenticação serverless de clientes por CPF (Lambda Python) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md |
| ADR-029 | Emulação local da Lambda de autenticação (pytest + AWS SAM CLI) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/029-emulacao-local-lambda.md |
| ADR-030 | Amazon EKS como cluster Kubernetes da fase 3 | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/030-cluster-kubernetes-eks.md |
| ADR-031 | Amazon RDS for PostgreSQL como banco gerenciado (justificativa formal do banco — RNF-027) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/031-banco-gerenciado-rds.md |
| ADR-032 | Stack de monitoramento Prometheus + Grafana + Loki | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/032-monitoramento-grafana-loki.md |
| ADR-033 | CI/CD multi-repo com GitHub Actions (com adendo de limitações constatadas) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/033-cicd-multi-repo.md |

A documentação das fases anteriores (Event Storming, Domain Storytelling, Linguagem Ubíqua, modelo de domínio, ADRs 001–025, RFC-001/002) permanece válida e versionada nas mesmas pastas — índice em [`docs/`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/tree/main/docs).

**Collection da API (Swagger/Postman)**: [openapi-fase3.json](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/openapi-fase3.json) (35 rotas, exportado do FastAPI) e [postman-collection-fase3.json](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/postman-collection-fase3.json) (inclui a rota `POST /auth` da function serverless, com variável `gateway_url` para SAM local ou AWS). O Swagger interativo fica em `/docs` na API em execução.

## 5. Relatório de análise de vulnerabilidades

A postura de segurança da fase 3 herda a bateria da fase 2. Os scanners executáveis localmente foram rodados na HEAD de 11/07/2026 e registrados abaixo com data. Os scanners do CI — trivy, gitleaks e pip-audit no [`security.yml`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/.github/workflows/security.yml), bandit no [`ci.yml`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/.github/workflows/ci.yml), ZAP no [`full-test-ci.yml`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/.github/workflows/full-test-ci.yml) e o CodeQL default setup, que é configuração do próprio GitHub, não workflow versionado — rodam a cada push, em cada PR e no cron semanal; última bateria verde em 03/09/2026 ([run Security do PR #14](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/runs/33763698992)).

### 5.1 Ferramentas e resultado na HEAD atual

Scans executados em **11/07/2026**, na árvore de trabalho da HEAD atual dos repositórios:

| Ferramenta | Tipo | Alvo | Resultado (2026-07-11) |
|---|---|---|---|
| bandit (`make security`, p3) | SAST (Static Application Security Testing, análise estática) | `src/` + `ui/` + `relay/` + `scripts/` (14.970 LoC) | **0 high / 0 medium** / 10 low (gate falha em high; os low são achados informativos revisados) |
| bandit (`make security`, p3-lambda) | SAST | `src/` da function | **0 issues** (nenhum achado em qualquer severidade) |
| pip-audit (`uv run --with pip-audit pip-audit`, p3) | SCA (Software Composition Analysis, vulnerabilidades em dependências) | ambiente resolvido do `uv.lock` | **0 vulnerabilidades conhecidas** (apenas o pacote local `pytstop 0.2.0` não auditável — não publicado no PyPI, esperado); reconfirmado no CI em 03/09/2026 após `cryptography` 50.0.1 ([PR #14](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/pull/14)) |
| OWASP ZAP (baseline) | DAST | API viva (stack compose dedicada) | Executado localmente em 11/07/2026 via `make dast`: FAIL 0 · WARN 0 · PASS 65 em 58 URLs (2 regras IGNORE do baseline; sumário persistido em [evidencias/zap-baseline-2026-07-11.txt](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/evidencias/zap-baseline-2026-07-11.txt)) |
| CodeQL (suíte de qualidade) | SAST semântico | código Python | Executado localmente em 11/07/2026 via `make codeql-quality`: 0 findings ativos (72 brutos, todos tratados por config/supressão justificada; 1 constante morta removida e 2 falsos positivos suprimidos com razão nesta rodada) |
| SonarQube (community, self-hosted) | Análise estática/qualidade — scan manual de fechamento (não é gate de CI por decisão, [TD-010/ADR-011](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/011-pipeline-seguranca-analise-estatica.md)) | `src/` (7.518 LoC) + coverage | Executado localmente em 11/07/2026: Quality Gate Passed — 0 bugs, 0 vulnerabilities, ratings A/A/A, 0% duplicação; 0 security hotspots, 0 code smells (os 143 do scan inicial foram zerados no PR #6); cobertura 94,6% no denominador do Sonar (o gate real mede 96,8% — divergência de universo documentada no `sonar-project.properties`); [screenshot do Quality Gate](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/evidencias/sonarqube-quality-gate-fase3.png) |
| trivy · gitleaks (`security.yml`) | SCA de imagem / segredos | imagem Docker (`pytstop:ci-scan`), árvore git | **Verdes no CI em 03/09/2026** ([run](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/actions/runs/33763698992)): trivy 0 HIGH/CRITICAL após a remoção do `pip` das imagens de runtime ([PR #14](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/pull/14) — o pip da base `python:3.14-slim` trazia msgpack e setuptools vendorizados com CVE) e gitleaks 0 achados; gitleaks também rodado localmente sobre o histórico completo dos cinco repositórios antes de torná-los públicos (únicos achados: segredos de demonstração já públicos desde a fase 2) |

Observação sobre o pip-audit: o `pip-audit` não é dependência do projeto — a execução usa `uv run --with pip-audit pip-audit`, que o instala efemeramente e audita o ambiente resolvido do lockfile.

### 5.2 Postura de segurança da fase 3

Além dos scans, as decisões de segurança específicas da fase:

- **Anti-enumeração de CPF na Lambda** (RN-022): CPF inexistente e cliente inativo recebem a mesma resposta `401`, sem distinguir os casos — teste dedicado na suíte da function ([ADR-028](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md));
- **Defense in depth na borda** ([ADR-027](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/027-api-gateway-aws.md)): o Lambda authorizer valida o JWT no gateway **e** o app revalida assinatura + RBAC — token inválido não chega ao app; token válido ainda passa pelo controle de papel;
- **Busca cega por CPF**: a function consulta o cliente por `documento_hash` (HMAC-SHA256 derivado da `ENCRYPTION_KEY`), a mesma proteção de PII do app — o CPF em claro não vai ao banco nem aos logs (scrub de PII herdado, [ADR-028](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md));
- **Segredos**: `JWT_SECRET`/`ENCRYPTION_KEY` compartilhados entre app e function via GitHub Secrets nos pipelines e variáveis Terraform no deploy; credenciais AWS Academy rotativas re-gravadas a cada sessão pelo runbook ([`aws-academy-setup.md`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/runbooks/aws-academy-setup.md)) — nada de segredo de longa duração em código;
- **Herança da fase 2** intacta no snapshot: webhook de orçamento assinado por HMAC, scrubber de PII nos logs, revogação de refresh token, rate limiter com storage compartilhado, mensagens de erro sem eco de dado pessoal.

### 5.3 Documentos completos

| Documento | URL |
|---|---|
| Scans de fechamento da fase 3 (bateria de 2026-07-11, resultados da seção 5.1) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/seguranca/scan-fase-3.md |
| Scans de fechamento da fase 2 (baseline herdada pelo snapshot) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/seguranca/scan-fase-2.md |
| Relatório de Vulnerabilidades (baseline OWASP API Top 10, fase 1) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/seguranca/relatorio-vulnerabilidades.md |
| Plano de segurança (camadas e ferramentas) | https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/seguranca/plano-seguranca.md |

## 6. Rastreabilidade requisito → evidência

Cada requisito obrigatório da fase 3 ([gap analysis](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/requisitos/fase3/gap-analysis-fase-3.md)) está mapeado para onde foi implementado/decidido e para a evidência de verificação. Os números do gate local (2026-07-11): p3 `make check` com **1.834 testes** e cobertura **96,4%**, `make test-integ` com **162 testes**, `make full-test` E2E verde; lambda com **34 testes** unitários + **3 de integração** e cobertura **100%** + `terraform validate`; repos infra com `terraform fmt -check` + `validate` verdes (seção 2).

### Requisitos funcionais

| ID | Requisito | Implementação / decisão | Evidência de verificação |
|---|---|---|---|
| RF-025 | Function serverless: valida CPF, consulta existência e status do cliente, emite JWT | Handler em [`postech-sw-arch-p3-lambda/src`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda) — validação com brutils, busca por `documento_hash`, emissão HS256 com claims compatíveis com o app ([ADR-028](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md), emulação local [ADR-029](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/029-emulacao-local-lambda.md)) | Gate local verde: 34 testes unitários no gate (incl. teste de paridade do hash/claims com o app) + 3 testes de integração com PostgreSQL real (testcontainers, alvo `make test-integ` à parte), cobertura 100%; `sam local` valida o runtime real — demo integrada executada em 11/07/2026 com códigos HTTP reais (seção 7) |
| RF-026 | API Gateway protegendo rotas sensíveis, com controle e roteamento | HTTP API + rota pública `POST /auth` + Lambda authorizer nas rotas protegidas, Terraform em [`p3-lambda/terraform`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda) ([ADR-027](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/027-api-gateway-aws.md)); app revalida JWT + RBAC (defense in depth) | `terraform validate` verde; testes do authorizer na suíte da lambda; **deploy AWS bloqueado por credenciais Academy** — runbook pronto ([`aws-academy-setup.md`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/runbooks/aws-academy-setup.md)); integração gateway→app no EKS é a rota de fechamento (pendência 4, seção 9) |
| RF-027 | Dashboards: volume diário de OS, tempo médio por status, erros de integrações | Dashboards **PytStop — Negócio** e **PytStop — Plataforma** provisionados como código em [`k8s/grafana.yaml`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/k8s/grafana.yaml); métricas de negócio instrumentadas na API (`src/compartilhado/infraestrutura/metrics.py` — OS criadas, duração por status, latência HTTP) ([ADR-032](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/032-monitoramento-grafana-loki.md)) | `make cd-local` sobe a stack completa no kind com os dashboards prontos (zero clique) — mesmos manifests do EKS; roteiro do vídeo demonstra ao vivo; testes das métricas dentro do `make check` |

### Requisitos não funcionais

| ID | Requisito | Implementação / decisão | Evidência de verificação |
|---|---|---|---|
| RNF-025 | 4 repositórios com CI/CD e deploy automático (homolog/produção); main protegida; PRs obrigatórios | Repos `p3`, `p3-lambda`, `p3-infra-k8s`, `p3-infra-db`, cada um com `ci.yml` + `cd.yml`; app/lambda: `homolog` → homologação e `main` → produção; infra: `homolog` = `terraform plan`, apply só na `main` (Adendo (b) do ADR-033). **Branch protection técnica ativa** na `main` dos cinco repositórios desde 03/09/2026 — PR obrigatório e checks obrigatórios; antes disso era inviável com repositórios privados no plano free, e a convenção de PR já valia (Adendos (a) e (e) do [ADR-033](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/033-cicd-multi-repo.md)) | Runs verdes nos 4 repos (links na seção 2); deploy por push comprovado no `p3` em `homolog` e `main` (CD de 01/08/2026); proteção da `main` verificável em *Settings → Branches* de cada repositório |
| RNF-026 | Terraform provisionando API Gateway, Function, banco gerenciado e cluster K8s com escalabilidade | EKS + node group em [`p3-infra-k8s`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-k8s) ([ADR-030](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/030-cluster-kubernetes-eks.md)); RDS em [`p3-infra-db`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-db) ([ADR-031](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/031-banco-gerenciado-rds.md)); gateway + functions em [`p3-lambda/terraform`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-lambda); HPA herdado em [`k8s/hpa.yaml`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/k8s/hpa.yaml) | `terraform fmt -check` + `validate` verdes nos 3 repos com IaC (gate local, 2026-07-11); **apply na AWS bloqueado por credenciais** — plano de desbloqueio 1 (seção 9); paridade local completa (kind + SAM) documentada na [RFC-003 §3](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md) |
| RNF-027 | Banco gerenciado + justificativa formal + diagrama ER | RDS PostgreSQL 16 via Terraform ([`p3-infra-db`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-infra-db)); justificativa formal no [ADR-031](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/031-banco-gerenciado-rds.md); ER atualizado com explicação dos relacionamentos na [RFC-003 §2](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md) | `terraform validate` verde; mesmo engine/versão do PostgreSQL local (paridade das 8+ migrações Alembic); ADR e RFC versionados |
| RNF-028 | Monitorar latência das APIs, CPU/memória do K8s, healthchecks/uptime, alertas de falha no processamento de OS | Prometheus + kube-state-metrics + cAdvisor (recursos), histograma de latência por rota na API, painéis de uptime/health e **5 regras de alerta provisionadas** (CPU > 80%, p95 > 300ms, 5xx > 1%, `outbox_dead > 0` — falha no processamento de OS —, API fora do ar) — [`k8s/`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/tree/main/k8s) ([ADR-032](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/032-monitoramento-grafana-loki.md)) | Stack verificada no kind via `make cd-local` (manifests idênticos aos do EKS); alertas visíveis em *Alerting → Alert rules* no Grafana; demonstração ao vivo no roteiro do vídeo |
| RNF-029 | Logs estruturados JSON com correlação entre requisições | structlog JSON com scrub de PII (herdado); middleware passa a **aceitar o `X-Request-ID` externo** vindo do gateway (`src/compartilhado/interfaces/middleware.py`), gerando UUID só na ausência; agregação com Loki + Promtail e consulta por `request_id` no Grafana ([RFC-003 §7](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md)) | Testes do middleware no `make check` (1.834 testes); consulta LogQL documentada no [`k8s/README.md`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/k8s/README.md); demonstração no bloco 7 do vídeo |
| RNF-030 | Documentação arquitetural completa: componentes (visão de nuvem), sequência (autenticação e abertura de OS), RFCs, ADRs, justificativa do banco + ER | [RFC-003](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md) (§4 componentes com nuvem/APIs/banco/monitoramento; §5 sequências de autenticação por CPF e abertura de OS; §2 ER) + ADRs 026–033 (seção 4.2) | Documentos versionados e renderizados pelo GitHub (Mermaid); diagrama de componentes replicado na seção 7 e nos READMEs dos 4 repos |

### Regras de negócio

| ID | Regra | Implementação / decisão | Evidência de verificação |
|---|---|---|---|
| RN-021 | O token emitido pela function é aceito pelas APIs protegidas | Dois emissores com públicos disjuntos (app = usuários internos; lambda = clientes), **mesmo segredo, mesmos claims, validador único** — o app valida o JWT da lambda sem mudança ([ADR-028](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md)) | Teste de paridade de claims/assinatura na suíte da lambda (34 testes, cobertura 100%); demo integrada local (lambda SAM + app no kind) no README do `p3-lambda` e no blocos 2 e 5 do vídeo (evidência executada na seção 7) |
| RN-022 | CPF inexistente ou cliente inativo não recebe token | Consulta de existência + status (`ativo`) no banco antes da emissão; `401` indistinto nos dois casos (anti-enumeração) — [ADR-028](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/028-autenticacao-serverless-cpf.md) | Testes unitários e de integração dedicados na suíte da lambda (cliente inexistente, inativo e ativo, com PostgreSQL real) |

**Clean Code / Clean Architecture** (herança verificada): os contratos de camadas do import-linter continuam como gate (`make lint-arch`, dentro do `make check`), e a cobertura sustentou-se em 96,4% com a fase 3 — a lambda nasceu com 100% para não rebaixar o padrão (risco mapeado no [gap analysis §5](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/requisitos/fase3/gap-analysis-fase-3.md)).

## 7. Desenho da arquitetura

Diagrama de componentes da fase 3 — visão de nuvem integrada: borda serverless (API Gateway + Lambdas), cluster EKS, banco gerenciado RDS e monitoramento, com a marcação de qual repositório provisiona o quê. Fonte única: [RFC-003 §4](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md).

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
        subgraph eks["Amazon EKS (ADR-030) — Terraform em p3-infra-k8s · manifests k8s/ no repo p3"]
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

### Paridade local (kind + SAM)

Evidências executadas em 11/07/2026 (demo integrada completa): `POST /auth` no gateway emulado → 200 com JWT (CPF semeado), 400 (malformado), 401 (inexistente e inativo, indistintos); rota protegida com Lambda authorizer emulado → 401 sem token, 403 com token adulterado, handler alcançado com token válido; token da lambda contra a API no kind → 403 "Papel nao autorizado" (assinatura e claims aceitos — a negação é do RBAC, prova do RN-021), contra 401 "Token invalido" do token adulterado. Collection Postman executada via newman: 28 assertions, 0 falhas (login, ciclo completo de OS até em_execucao, `/auth` da lambda).

O desenvolvimento é **100% local** ([ADR-026](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/026-cloud-alvo-aws-academy.md)): a AWS entra só para validação e demo, dentro de sessões do Learner Lab. No espelho local, a caixa `borda` é substituída pelo `sam local start-api` (gateway emulado + function, com o runtime real `python3.13` em container — [ADR-029](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/adr/fase3/029-emulacao-local-lambda.md)) e o EKS pelo **kind** (`make cd-local`). Mesmos manifests base, mesmo PostgreSQL 16, mesma stack de monitoramento — o restante do diagrama é idêntico. As duas lacunas de paridade (roteamento gateway→app e authorizer não existem localmente) são aceitas e documentadas: a validação JWT redundante no app garante a mesma semântica de segurança. Tabela componente a componente na [RFC-003 §3](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md).

## 8. Conteúdo do PDF de submissão

O PDF entregue no portal do aluno é gerado a partir deste documento pelo [`scripts/build-entrega-pdf.sh`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/scripts/build-entrega-pdf.sh), que acrescenta uma capa ABNT no início, renderiza os diagramas Mermaid como imagens e converte os links relativos em absolutos. A seção 9 (Pendências) é um checklist interno da equipe e **não** é incluída no PDF submetido.

O PDF contém os quatro itens exigidos pelo enunciado:

1. **Links dos 4 repositórios** (seção 2, mais o repo de processo): app, lambda, infra-k8s, infra-db.
2. **Link do vídeo** de até 15 minutos (seção 3 — preenchido após a gravação).
3. **Links das documentações** (seção 4): enunciado transcrito, gap analysis, RFC-003, ADRs 026–033, READMEs dos cinco repositórios e runbooks de operação.
4. **Confirmação do usuário `soat-architecture`** adicionado a todos os repositórios (seções 2 e 9).

Mais os anexos de evidência: o desenho da arquitetura (seção 7), a rastreabilidade requisito → evidência (seção 6) e o relatório de análise de vulnerabilidades (seção 5).

## 9. Pendências para fechar a entrega

Ações manuais que permanecem com a equipe (nenhuma bloqueia a navegação dos repositórios). Os planos de desbloqueio detalhados estão versionados no repo [`postech-sw-arch-p3-docs`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs) — [orquestrador](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/superpowers/plans/2026-07-11-orquestrador-desbloqueio.md) + planos 1–3:

| # | Pendência | Onde |
|---|---|---|
| 1 | Gravar o vídeo seguindo o [roteiro](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/blob/main/docs/entrega/fase3/roteiro-video.md), publicar (YouTube/Vimeo, não listado) e preencher o link na seção 3 (marcador `VIDEO-LINK-FASE-3`) | `docs/entrega/fase3/entrega-fase-3.md` |
| 2 | Adicionar `soat-architecture` como colaborador de leitura nos **cinco repositórios** (`p3`, `p3-lambda`, `p3-infra-k8s`, `p3-infra-db`, `p3-docs`): em 03/09/2026 o usuário não constava em nenhum deles (nem no `p2`). Com os repositórios públicos o acesso de leitura já existe, mas o enunciado pede a adição explícita e a confirmação neste documento | GitHub → Settings → Collaborators de cada repo (ou `gh api -X PUT repos/<org>/<repo>/collaborators/soat-architecture -f permission=pull`) |
| 3 | ~~Cota do GitHub Actions~~ **Resolvida em 01/08/2026**: pipelines executados nos 4 repos com runs verdes (links na seção 2); Security do `p3` corrigido em 03/09/2026 ([PR #14](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/pull/14)); repositórios públicos desde 03/09/2026 (minutos ilimitados) | [Plano de desbloqueio 2](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/superpowers/plans/2026-07-11-desbloqueio-2-cota-actions.md) (executado) |
| 4 _(bloco "deploy automatizado" do vídeo)_ | Deploy AWS de ponta a ponta (RDS → EKS → app → gateway/lambda) numa sessão do Academy. O run verde do `cd.yml` disparado por push já existe (01/08/2026: imagens no GHCR + deploy no kind do runner em `main` e `homolog`; job EKS pulado sem secrets AWS) e serve como evidência mínima de deploy automatizado; a demonstração na nuvem depende da sessão do Academy. O `make cd-local` sozinho é comando manual e só serve de fallback narrado | [Plano de desbloqueio 1](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/superpowers/plans/2026-07-11-desbloqueio-1-aws-deploy.md) + runbook [`aws-academy-setup.md`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/runbooks/aws-academy-setup.md) |
| 5 | Mergear as alterações finais (link do vídeo) na `main`, regerar o PDF e submeter no portal do aluno | [Plano de desbloqueio 3](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/superpowers/plans/2026-07-11-desbloqueio-3-entrega-final.md) |

---

> [↑ Raiz do projeto](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3) · [↑ Entrega Fase 3](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/tree/main/docs/entrega/fase3)
