# Roteiro do Vídeo — Fase 3

> [↑ Raiz do projeto](../../../README.md) · [↑ Entrega Fase 3](entrega-fase-3.md)

> **Versão**: 1.0 — Fase 3.

Duração alvo: ~13min (folga dentro do limite de 15 min — a soma dos blocos abaixo fecha em 13min; cronometrar no ensaio). O enunciado exige demonstrar, nesta ordem: **autenticação com CPF**, **execução da pipeline CI/CD**, **deploy automatizado**, **consumo das APIs protegidas**, **dashboard de monitoramento com análise ao vivo** e **logs e traces em execução**.

**Dois caminhos por bloco**: cada bloco traz o caminho **AWS** (se a sessão do Academy estiver ativa e o deploy do [plano de desbloqueio 1](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/superpowers/plans/2026-07-11-desbloqueio-1-aws-deploy.md) tiver sido feito) e o caminho **local espelho** (kind + SAM — paridade documentada na [RFC-003 §3](../../arquitetura/rfc/fase3/rfc-003-gateway-serverless-observabilidade.md)). Gravar UM caminho por bloco; ao usar o local, dizer na fala que é o espelho documentado da nuvem.

**Pré-gravação (não aparece no vídeo):**

- `make k8s-down` se houver cluster de sessão anterior (o bloco 3 grava o provisionamento do zero);
- Docker com memória suficiente para o cluster completo (no Colima: `colima start --memory 4`);
- clonar os repos irmãos (`postech-sw-arch-p3-lambda` ao lado do `p3`); no lambda: `uv sync` + SAM CLI instalado;
- criar o `env.json` do SAM com os segredos de demo do app ([`k8s/secret.yaml`](../../../k8s/secret.yaml)), para o token da lambda ser aceito pelo app:

  ```json
  {
    "AutenticacaoCpfFunction": {
      "DATABASE_URL": "postgresql://pytstop:pytstop-demo@host.docker.internal:5432/pytstop",
      "JWT_SECRET": "demo-jwt-secret-pytstop-fase2-no-minimo-32-bytes",
      "ENCRYPTION_KEY": "C9I0jOzZ9kJBTY0akV3TvBO2wa1JcuAdR-Wctnzee6I="
    }
  }
  ```

- abas prontas no browser: README do repo `p3`, aba Actions (ou terminal do gate local), Grafana (`localhost:3000`), Jaeger (`localhost:16686`);
- ensaio completo pelo menos uma vez (o `make cd-local` leva ~3-5 min em máquina fria);
- CPFs de demonstração: os clientes semeados usam documentos sintéticos válidos no brutils (ex.: `11144477735` — [`ui/seed.py`](../../../ui/seed.py)); ter um CPF de cliente ativo e um inexistente colados num rascunho.

## Estrutura

### 1. Abertura + arquitetura (1 min)

- Apresentação: turma 15SOAT, grupo PytStop, fase 3 do Tech Challenge.
- Abrir o [README](../../../README.md) no GitHub e percorrer o diagrama Mermaid da fase 3 (fonte: RFC-003 §4): borda serverless (API Gateway + Lambda de autenticação + authorizer), app no EKS com HPA, RDS PostgreSQL, monitoramento Prometheus/Grafana/Loki/Jaeger — e os 4 repositórios com CI/CD próprio.

**Fala**: "A fase 3 leva a oficina à nuvem: autenticação serverless por CPF na borda, cluster gerenciado, banco gerenciado e observabilidade completa — segregados em quatro repositórios com pipeline cada."

**Evidência no ar**: diagrama de componentes visível e narrado.

### 2. Autenticação com CPF (2min30s)

**Caminho local (SAM + app no kind)** — com o cluster do bloco 3 já de pé no ensaio (a gravação pode inverter a ordem de captura; na edição este bloco vem primeiro):

```bash
# expor o Postgres do cluster para a lambda (terminal separado, deixar rodando):
kubectl --context kind-pytstop -n pytstop-infra port-forward svc/postgres 5432:5432

# no repo postech-sw-arch-p3-lambda — gateway emulado + function (runtime real python3.13):
sam local start-api --env-vars env.json

# CPF de cliente ativo → 200 com JWT:
curl -s -X POST http://localhost:3000/auth -H "Content-Type: application/json" \
  -d '{"cpf": "11144477735"}'

# CPF válido mas inexistente na base → 401 (RN-022, resposta indistinta):
curl -si -X POST http://localhost:3000/auth -H "Content-Type: application/json" \
  -d '{"cpf": "52998224725"}' | head -1

# guardar o token para o bloco 5:
TOKEN=$(curl -s -X POST http://localhost:3000/auth -H "Content-Type: application/json" \
  -d '{"cpf": "11144477735"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

**Caminho AWS** (gateway real — usar as URLs do `terraform output` do repo lambda):

```bash
cd postech-sw-arch-p3-lambda/terraform && terraform output
curl -s -X POST "$(terraform output -raw auth_url_prod)" \
  -H "Content-Type: application/json" -d '{"cpf": "11144477735"}'
```

**Fala**: "A function valida o formato do CPF com brutils, consulta a existência e o status do cliente por hash cego no banco e emite um JWT com o mesmo segredo e claims do app — CPF inexistente ou cliente inativo recebe o mesmo 401, sem vazar qual dos dois."

**Evidência no ar**: 200 com `access_token` para o cliente ativo; 401 para o CPF inexistente; SAM logando a invocação com o runtime `python3.13`.

### 3. Execução da pipeline CI/CD (1min30s)

**Caminho AWS/Actions** (se a cota tiver renovado): abrir **Actions → CI/CD** em um dos 4 repos e mostrar a run verde — jobs de gate (lint, typecheck, segurança, testes ≥ 95%) e deploy por branch (`homolog` → homologação, `main` → produção).

**Caminho local espelho** (estado atual — cota esgotada, [ADR-033](../../arquitetura/adr/fase3/033-cicd-multi-repo.md)): mostrar os workflows commitados (`.github/workflows/ci.yml` e `cd.yml` nos 4 repos) e rodar o gate espelho ao vivo no repo lambda (o mais rápido):

```bash
# repo postech-sw-arch-p3-lambda:
make gate     # lint + mypy strict + bandit + 34 testes (cobertura 100%) + terraform validate
```

**Fala**: "Cada repositório tem CI e CD próprios com deploy automático por branch; com a cota do Actions esgotada, o gate local é o espelho obrigatório dos mesmos passos — no app são 1.834 testes com 96,39% de cobertura."

**Evidência no ar**: workflows nos 4 repos OU run verde; `make gate` terminando verde com cobertura 100%.

### 4. Deploy automatizado (1min30s)

> Este bloco precisa de UMA das duas evidências de automação: run verde do `cd.yml` disparado por push (cota do Actions renovada — Desbloqueio 2) ou deploy na AWS via pipeline (Desbloqueio 1). O `make cd-local` abaixo é o fallback narrado ("espelho local do que o pipeline executa") — deixe explícito na fala que o gatilho real é o push.

**Caminho local** (mesmos estágios do job `deploy` do `cd.yml` — paridade local × pipeline):

```bash
# repo postech-sw-arch-p3 (raiz):
make cd-local
```

Narrar os estágios enquanto rolam: cluster kind + PostgreSQL → build da imagem com tag por SHA + `kind load` → `kubectl apply` dos manifests (API, relay, Redis, Mailpit, HPA **e a stack de monitoramento**: Prometheus, Grafana, Loki, Promtail, kube-state-metrics, Jaeger) → Job de migração antes do rollout → smoke test `GET /api/v1/saude`.

```bash
kubectl --context kind-pytstop get pods -n pytstop
```

**Caminho AWS**: na ordem multi-repo do ADR-033 — `terraform apply` no `p3-infra-db` (RDS), depois `p3-infra-k8s` (EKS), deploy do app pelo `cd.yml` (job `deploy-eks`, overlay `k8s/overlays/eks`), e `terraform apply` no `p3-lambda` (gateway + functions). Mostrar `kubectl get pods` contra o EKS.

**Fala**: "O deploy é o mesmo fluxo do CD: infra provisionada por Terraform, imagem imutável por SHA, migração como gate antes do rollout e smoke test no final."

**Evidência no ar**: smoke OK ao final; pods 1/1 Running, incluindo grafana, loki, prometheus e jaeger.

### 5. Consumo das APIs protegidas com o token (2 min)

Port-forward da API (terminal separado, deixar rodando):

```bash
kubectl --context kind-pytstop -n pytstop port-forward svc/pytstop-api 18000:8000
```

Sequência gravada:

1. **Sem token → barrado**: `curl -si http://localhost:18000/api/v1/ordens-de-servico/ | head -1` → **401**.
2. **Token do cliente (bloco 2) aceito pelo validador do app** (RN-021 — mesmo segredo, mesmos claims): `curl -si -H "Authorization: Bearer $TOKEN" http://localhost:18000/api/v1/ordens-de-servico/ | head -1` → **403** (assinatura aceita; o RBAC nega a rota interna ao papel `cliente` — defense in depth). No caminho AWS, a rota protegida de exemplo do gateway responde **200** com o token e **401** sem ele, barrando na borda pelo authorizer.
3. **Fluxo de negócio com usuário interno**: Swagger em **http://localhost:18000/docs** → `POST /api/v1/autenticacao/login` (`admin@pytstop.dev` / senha de demo) → **Authorize** → `POST /api/v1/ordens-de-servico/` com serviços e peças → **201** com id; `GET` do id → `situacao` no vocabulário do challenge.

**Fala**: "O mesmo validador atende os dois emissores: o token do cliente emitido pela lambda passa na assinatura e cai no controle de papel, e o usuário interno opera o fluxo completo de OS — token inválido nem chega ao app quando o gateway está na frente."

**Evidência no ar**: 401 sem token; 403/200 com o token da lambda (conforme o caminho); 201 + `situacao` no fluxo interno.

### 6. Dashboard Grafana ao vivo (2min30s)

Port-forward do Grafana (deixar rodando) e gerar carga + dados de negócio:

```bash
kubectl --context kind-pytstop -n pytstop port-forward svc/grafana 3000:3000

# dados de negócio (7 clientes, 10 veículos, 8 OS em estados variados) via API do cluster:
BACKEND_URL=http://localhost:18000 make seed-demo

# carga contínua para os painéis de latência/tráfego (deixar rodando durante o bloco):
while true; do curl -s -o /dev/null http://localhost:18000/api/v1/saude; sleep 0.2; done
```

Abrir **http://localhost:3000** (acesso anônimo entra como *Viewer*) → pasta *PytStop*:

- **PytStop — Negócio**: volume de OS criadas (24h e por hora), tempo médio de OS por status, erros de integração da outbox, visão NOC — os painéis mexem com o seed que acabou de rodar;
- **PytStop — Plataforma**: latência p50/p90/p99 por rota subindo com o loop de carga, taxa de 5xx, CPU/memória por pod, uptime/health;
- *Alerting → Alert rules*: as 5 regras provisionadas (CPU > 80%, p95 > 300ms, 5xx > 1%, `outbox_dead > 0` — falha no processamento de OS —, API fora do ar).

**Fala**: "Tudo é observabilidade-como-código: datasources, dashboards e alertas sobem provisionados do git — os painéis de negócio respondem aos dados criados agora e os de plataforma, à carga ao vivo."

**Evidência no ar**: painéis dos dois dashboards atualizando ao vivo; lista das regras de alerta na pasta PytStop.

### 7. Logs no Loki + trace no Jaeger (1min30s)

Capturar um `request_id` real e persegui-lo nas duas vistas:

```bash
# capturar o token interno uma vez (sem digitação ao vivo):
TOKEN_INTERNO=$(curl -s -X POST http://localhost:18000/api/v1/autenticacao/login -H "Content-Type: application/json" -d '{"email":"admin@pytstop.com.br","senha":"<senha de demo>"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# o middleware devolve o X-Request-ID (aceita o id externo do gateway — RNF-029):
curl -si http://localhost:18000/api/v1/ordens-de-servico/ \
  -H "Authorization: Bearer $TOKEN_INTERNO" | grep -i x-request-id
```

- No Grafana, *Explore* → datasource **Loki** → `{app="pytstop-api"} |= "<request_id>"` (correlação por filtro de linha, nunca por label — [`k8s/README.md`](../../../k8s/README.md)): as linhas JSON estruturadas da requisição, com o mesmo `request_id`.
- Jaeger (port-forward `svc/jaeger 16686:16686`, ou o datasource Jaeger no próprio Grafana) → serviço `pytstop-api` → *Find Traces* → abrir 1 trace: span do endpoint FastAPI com as queries SQLAlchemy aninhadas.

**Fala**: "Logs JSON com scrub de PII e request id que nasce na borda e atravessa a cadeia; o mesmo request tem as duas vistas — a linha do tempo nos logs e o trace distribuído no Jaeger."

**Evidência no ar**: logs filtrados pelo `request_id` no Loki; um trace aberto com spans `fastapi` + `sqlalchemy`.

### 8. Encerramento (30 s)

- Qualidade sustentada: **1.834 testes** com cobertura **96,39%** no app (gate ≥ 95%), lambda com **34 testes** e **100%** de cobertura, contratos de camadas por import-linter, scans de segurança verdes na HEAD (bandit + pip-audit — [entrega-fase-3.md §5](entrega-fase-3.md)).
- Decisões registradas: ADRs 026–033 + RFC-003; rastreabilidade completa em [entrega-fase-3.md](entrega-fase-3.md).
- Quatro repositórios (+ docs) privados, compartilhados com `soat-architecture`.

## Notas de Produção

- Terminal com fonte grande (14pt+); Grafana e Swagger em tela cheia nos blocos 5–7.
- Gravar o bloco 4 sem cortes (o provisionamento é a prova); acelerar esperas na edição com timestamp visível.
- Deixar os port-forwards rodando desde a preparação — não gravar a digitação deles.
- Conferir antes de gravar: `make cd-local` verde de ponta a ponta, `sam local start-api` respondendo, dashboards populando.
- No caminho AWS: rodar o runbook [`aws-academy-setup.md`](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3-docs/blob/main/docs/runbooks/aws-academy-setup.md) ANTES (credenciais expiram em ~4h) e `terraform destroy` DEPOIS da gravação (budget do Academy).
- Ter o CPF de demo, o token da lambda e as credenciais internas colados num rascunho para não digitar ao vivo.

> [↑ Raiz do projeto](../../../README.md) · [↑ Entrega Fase 3](entrega-fase-3.md)
