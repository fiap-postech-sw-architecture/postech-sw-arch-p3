# CI/CD multi-repo com GitHub Actions

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

O Tech Challenge da fase 3 exige o projeto organizado em **quatro repositórios separados**, cada um com **CI/CD implementado** e **deploy automático das branches de homologação e produção**, com **branch main protegida** (sem commits diretos) e **Pull Requests obrigatórios** — ver [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md) e o requisito RNF-025 no [gap analysis](../../../requisitos/fase3/gap-analysis-fase-3.md).

O estado herdado: o p2 era um monorepo com 6 workflows (CI com gates de lint/typecheck/segurança/cobertura, CD para kind efêmero e cloud — [ADR-019](../fase2/019-pipeline-cicd-deploy.md)). Na fase 3 o código se espalha por quatro repositórios (gap analysis, §3): `postech-sw-arch-p3` (aplicação), `postech-sw-arch-p3-lambda` (function serverless), `postech-sw-arch-p3-infra-k8s` (Terraform do EKS — [ADR-030](030-cluster-kubernetes-eks.md)) e `postech-sw-arch-p3-infra-db` (Terraform do RDS — [ADR-031](031-banco-gerenciado-rds.md)).

Duas restrições operacionais pesam:

1. **Credenciais AWS Academy rotativas** — cada sessão do lab emite credenciais novas (~4h), inviabilizando OIDC/segredos de longa duração; o fluxo de atualização está no runbook `aws-academy-setup.md` (repo `postech-sw-arch-p3-docs`);
2. **Cota do GitHub Actions esgotada** — os pipelines novos não são executáveis no CI até a renovação da cota (gap analysis, §5), o que obriga um espelho local dos gates.

**Como estruturar CI/CD em quatro repositórios, com deploy automático homolog/produção, sob credenciais rotativas e sem minutos de Actions?**

## Decisão

Adotar **GitHub Actions em cada um dos quatro repositórios**, com um padrão uniforme por repo — sem orquestração automática entre repositórios.

- **`ci.yml` por repo**, com os checks adequados ao conteúdo:
  - **`p3`** (aplicação): lint, typecheck, segurança e testes com **cobertura ≥ 95%** (padrão herdado do p2);
  - **`p3-lambda`**: os mesmos gates de código Python (cobertura ≥ 95% — a lambda nasce testada para não rebaixar o padrão, gap analysis §5) + `sam validate`;
  - **`p3-infra-k8s`** e **`p3-infra-db`**: `terraform fmt -check`, `terraform validate` e `tflint`.
- **`cd.yml` por repo com deploy automático por branch**: push em **`homolog` → ambiente de homologação**; push em **`main` → produção** — o mapeamento exato exigido pelo challenge. Autenticação via **credenciais AWS Academy em GitHub Secrets**, rotacionadas a cada sessão do lab conforme o runbook `aws-academy-setup.md`.
- **Ordem de deploy entre repos documentada, não automatizada**: `infra-db` → `infra-k8s` → `app` → `lambda` (ordem original deste ADR corrigida — ver Adendo (c)). O gatilho entre repos é manual (README/runbook); não há workflow cross-repo disparando cadeia de deploys — acoplamento desnecessário para quatro pipelines pequenos com deploy pouco frequente.
- **Branch protection na `main` dos quatro repos** (sem commit direto, PR obrigatório), ativada **ao final do bootstrap** — durante o bootstrap dos repositórios o push direto foi autorizado pelo usuário; a proteção fecha antes da entrega. **Constatada inviável na org atual — ver Adendo (a)**.
- **Espelho local obrigatório enquanto a cota do Actions estiver esgotada**: os pipelines ficam commitados e corretos, mas não executáveis; antes de cada push roda-se o gate local equivalente — `make check` no app e alvo `make gate` equivalente nos demais repos (fmt/validate/tflint, sam validate, testes). Quando a cota renovar, o CI passa a ser o gate canônico sem mudança nos workflows.

## Alternativas Consideradas

* GitHub Actions por repo, padrão uniforme, sem orquestração cross-repo
* Monorepo com paths-filter
* Reusable workflows num repo central
* GitLab CI

### GitHub Actions por repo, padrão uniforme, sem orquestração cross-repo

* Bom, porque cumpre o RNF-025 na letra: 4 repos, cada um com CI/CD próprio e deploy automático homolog/produção
* Bom, porque reusa a experiência e os gates do p2 ([ADR-019](../fase2/019-pipeline-cicd-deploy.md)) — o `ci.yml` do app é evolução direta, não reescrita
* Bom, porque quatro pipelines pequenos e independentes são simples de entender e depurar — cada repo conta sua própria história no PR
* Ruim, porque a ordem de deploy entre repos fica por disciplina documentada, não por automação — aceito: a cadência de deploy de infra é baixa e a demo é conduzida manualmente
* Ruim, porque secrets rotativos do Academy precisam ser atualizados em quatro repos a cada sessão — mitigado pelo passo único do runbook

### Monorepo com paths-filter

* Bom, porque manteria o fluxo da fase 2 (um repo, workflows filtrando por diretório) com atomicidade entre app e infra
* Ruim, porque o challenge **exige quatro repositórios separados** — a alternativa falha o requisito eliminatório, por melhor que seja tecnicamente

### Reusable workflows num repo central

* Bom, porque eliminaria duplicação entre os quatro `ci.yml`/`cd.yml` (DRY entre pipelines)
* Ruim, porque é indireção prematura: são quatro pipelines pequenos com conteúdos diferentes (Python app, lambda SAM, dois Terraform) — o que há de comum é pouco, e a camada extra dificulta ler e depurar cada pipeline isoladamente
* Ruim, porque adiciona um ponto único de mudança que quebra os quatro repos de uma vez, sob uma cota de Actions que hoje nem permite validar a quebra

### GitLab CI

* Bom, porque está na lista exemplificativa do challenge ("GitHub Actions, GitLab CI, etc.")
* Ruim, porque toda a stack atual é GitHub (repos, PRs, secrets, histórico das fases 1–2) — migrar de plataforma para trocar de sintaxe de pipeline é custo sem ganho algum

## Consequências

### Positivas

* RNF-025 coberto: 4 repos com CI/CD, deploy automático homolog/produção, main protegida e PR obrigatório — a proteção técnica da `main` mostrou-se inviável no plano atual da org; a exigência é cumprida por convenção documentada (ver Adendo (a))
* Pipelines independentes tornam o escopo de cada mudança explícito: PR de infra não roda testes de app, PR de app não toca Terraform
* O espelho local mantém o padrão de qualidade da fase 2 mesmo sem minutos de Actions — os gates não afrouxam, apenas mudam de executor temporariamente

### Negativas

* Enquanto a cota do Actions não renovar, "pipelines funcionais" só é demonstrável localmente — risco para o entregável do vídeo (execução da pipeline); mitigação: renovar a cota antes da gravação e manter os workflows prontos para o primeiro run verde
* Credenciais em GitHub Secrets (em vez de OIDC) são o trilho possível no Academy, mas exigem rotação manual a cada sessão — esquecer a rotação faz o CD falhar com credencial expirada
* A ordem de deploy manual entre repos pode ser violada por descuido (ex.: app antes do banco existir) — mitigada pela documentação no README de cada repo e pelo runbook da demo

### Neutras

* Conteúdo exato dos workflows (matrizes, versões de actions, nomes de jobs) vive em cada repositório, fora deste ADR
* Os workflows auxiliares do p2 (`security.yml`, `full-test-ci.yml`, workflows Claude) permanecem só no repo principal (gap analysis, §4); este ADR trata do padrão ci/cd dos quatro repos exigidos
* Se a rotação de secrets se provar dolorosa, promover a autenticação a OIDC quando houver conta AWS estável é evolução compatível — muda o passo de login, não o desenho

## Decisões Relacionadas

- [ADR-019](../fase2/019-pipeline-cicd-deploy.md): o pipeline monorepo da fase 2, cuja estrutura de gates este ADR replica por repositório
- [ADR-030](030-cluster-kubernetes-eks.md): o `cd.yml` do `p3-infra-k8s` provisiona o EKS; o do `p3` faz deploy da aplicação nele
- [ADR-031](031-banco-gerenciado-rds.md): o `p3-infra-db` é o primeiro da ordem de deploy — cluster e app dependem do banco existir
- [ADR-032](032-monitoramento-grafana-loki.md): dashboards e regras de alerta versionados passam pelos mesmos PRs/gates do repo principal
- [ADR-028](028-autenticacao-serverless-cpf.md): define o conteúdo que o pipeline do `p3-lambda` empacota e valida (`sam validate`)

## Notas

* Requisito formal: RNF-025 ([gap-analysis-fase-3.md](../../../requisitos/fase3/gap-analysis-fase-3.md)); exigência original em [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md)
* Rotação das credenciais AWS Academy e atualização dos secrets: runbook `aws-academy-setup.md` no repo `postech-sw-arch-p3-docs`
* A restrição de cota do GitHub Actions e o gate local espelho estão registrados como risco no gap analysis (§5); este ADR os assume como condição operacional temporária, não como desenho

## Adendo (2026-07-11) — limitações constatadas e decisões complementares

A implementação dos pipelines nos quatro repositórios expôs limitações que este ADR não previa. As decisões abaixo complementam (e, onde indicado, substituem) o corpo do documento.

### (a) Branch protection: inviável na org atual

A ativação da branch protection na `main`, prevista na Decisão para "o final do bootstrap", é **inviável** na organização atual: plano free com repositórios privados — a API do GitHub responde **HTTP 403 "Upgrade to GitHub Pro"** nos quatro repos. A mesma limitação existe no p2 desde a fase 2, precedente já aceito pela banca.

* Mitigação decidida: **fluxo de PR obrigatório por convenção documentada** — o workflow canônico do projeto proíbe commit direto na `main`; todo o histórico das fases 1–3 evidencia o cumprimento.
* Opções registradas caso a banca exija a proteção técnica: **upgrade da org para o plano Team** ou **tornar os repositórios públicos no momento da entrega**.

### (b) Homolog nos repos de infra: `terraform plan`

Nos repositórios `p3-infra-k8s` e `p3-infra-db`, o push em `homolog` executa **`terraform plan`** (estágio de homologação de infra); o **apply automático acontece só na `main`**. Com um único Learner Lab e budget mínimo ([ADR-026](026-cloud-alvo-aws-academy.md)), um ambiente homolog duplicado de infraestrutura (segundo EKS + segundo RDS) é inviável. App e lambda mantêm homolog real: overlay/workspace de stage próprios.

### (c) Ordem de deploy corrigida

A ordem passa a ser **`infra-db` → `infra-k8s` → `app` (p3) → `lambda`/gateway** — a rota HTTP_PROXY do gateway exige a URL pública do app no EKS (Service LoadBalancer), que só existe **após** o deploy do app. Esta ordem **substitui** a ordem `infra-db → infra-k8s → lambda → app` registrada na Decisão deste ADR.

### (d) Gestão de segredos de runtime

Os segredos de runtime (`JWT_SECRET`, `ENCRYPTION_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`) fluem por **GitHub Secrets** → `TF_VAR_*` (repos Terraform) ou `kubectl create secret` (deploy no EKS) nos pipelines; no fluxo manual, `terraform.tfvars`/arquivos de env locais git-ignored. AWS Secrets Manager e SSM Parameter Store foram **descartados** pelas restrições de IAM/KMS do Learner Lab ([ADR-026](026-cloud-alvo-aws-academy.md)).

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
