# Cloud alvo da fase 3: AWS via conta AWS Academy Learner Lab

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

A fase 3 do Tech Challenge exige um conjunto **integrado** de recursos de nuvem que a fase 2 não exigia: function serverless de autenticação (RF-025), API Gateway na frente das rotas (RF-026), banco de dados gerenciado com justificativa formal (RNF-027) e Terraform provisionando gateway, function, banco e cluster Kubernetes na nuvem (RNF-026) — ver o [gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md).

Na fase 2 a nuvem foi o **Azure**, via Azure for Students, como ambiente de demonstração opcional ([ADR-025](../fase2/025-ambiente-cloud-demonstracao.md)). Aquela decisão resolvia um problema diferente (URL pública para a banca, aditiva ao kind); a fase 3 muda o problema: a nuvem deixa de ser demonstração e passa a ser **requisito do enunciado**, e o material didático da fase aponta um provedor específico. O fichamento do módulo Serverless (repo `postech-sw-arch-p3-docs`, `docs/superpowers/research/serverless.md`) registra que as 6 aulas usam **exclusivamente AWS** — Lambda, API Gateway, ECS Fargate, DynamoDB, Cognito, SAM — sem qualquer menção a Azure Functions ou equivalentes. Já o módulo API-Gateway (repo `postech-sw-arch-p3-docs`, `docs/superpowers/research/api-gateway.md`) divide-se entre Azure APIM e Kong, **sem uma única menção a AWS**, mas é o módulo Serverless que amarra function + gateway + banco no desenho integrado que o challenge cobra.

A FIAP disponibiliza, por convite, contas **AWS Academy Learner Lab** — um ambiente AWS real, porém com restrições fortes:

- **Sessões de ~4h com credenciais temporárias**: cada _Start Lab_ emite novo trio access key + secret + session token; ao fim da sessão as credenciais expiram e os recursos de computação são pausados.
- **Role fixa `LabRole`**: é proibido criar IAM users ou roles — o Terraform **não gerencia IAM**; todo recurso que precisa de role recebe a `LabRole` pré-existente.
- **Budget limitado** (~US$ 50–100): esgotado o budget, a conta é **encerrada** — não pausada.
- **Regiões restritas**: na prática, `us-east-1`.

O problema, portanto: **qual nuvem e qual conta usar como alvo da fase 3, dado que o enunciado exige serverless + gateway + banco gerenciado integrados, o material aponta AWS, e as opções de conta têm restrições e custos muito diferentes?**

## Decisão

Adotar a **AWS como cloud alvo da fase 3, via conta AWS Academy Learner Lab (convite FIAP)**, e desenhar toda a infraestrutura para conviver com as restrições do Learner Lab:

- **Credenciais efêmeras como premissa, não exceção.** A cada _Start Lab_, o trio access key + secret + session token muda; os secrets de CI (repos de infra) precisam ser **re-gravados a cada sessão** antes de qualquer run que toque a AWS. O runbook de sessão documenta esse passo como primeiro item.
- **Terraform sem IAM.** Nenhum módulo Terraform cria users, roles ou policies; onde um recurso exige role (Lambda, EKS, etc.), referencia-se a `LabRole` existente por _data source_. Isso é uma restrição dura da conta, não uma escolha.
- **State do Terraform local, não versionado.** Backend remoto (S3 + lock) é dispensado: a vida útil de qualquer provisionamento é a janela de uma sessão de lab (~4h) ou, no máximo, o intervalo até o `terraform destroy` pós-demo. Um backend remoto sobreviveria ao state que deveria proteger — complexidade sem benefício aqui.
- **`terraform destroy` pós-demo obrigatório.** O budget é pequeno e o encerramento por esgotamento é definitivo; recursos caros (EKS, RDS, NAT) não ficam de pé fora de sessões de trabalho/demo. O desenvolvimento do dia a dia acontece **100% local** (kind + docker-compose + emulação da Lambda, [ADR-029](029-emulacao-local-lambda.md)), reservando a AWS para validação e demonstração.
- **Região fixa `us-east-1`** em todos os módulos Terraform.

A conta AWS Academy **ainda não foi ativada** no momento desta decisão — o convite está previsto, mas tudo é validado localmente até lá. A decisão é registrada agora para que os repos de infra, a Lambda e o gateway nasçam já desenhados para as restrições do Learner Lab, em vez de precisarem de retrofit.

## Alternativas Consideradas

* AWS via conta AWS Academy Learner Lab (convite FIAP)
* Azure for Students (nuvem da fase 2, ADR-025)
* Conta AWS pessoal

### AWS via conta AWS Academy Learner Lab (convite FIAP)

* Bom, porque é AWS — o provedor de **100% do material do módulo Serverless** (Lambda, API Gateway, SAM, aulas 01–06 do fichamento): o que se aprende nas aulas é o que se provisiona no challenge, sem tradução de conceitos entre provedores
* Bom, porque o custo é coberto pelo budget do Academy — sem cartão de crédito pessoal e sem risco financeiro próprio
* Bom, porque é institucional: o convite vem da FIAP, alinhado ao que a banca espera encontrar na entrega
* Ruim, porque as sessões de ~4h com credenciais rotativas impõem atrito operacional (re-gravar secrets de CI a cada sessão) e inviabilizam qualquer ambiente sempre-no-ar
* Ruim, porque a proibição de criar IAM users/roles engessa o Terraform (tudo via `LabRole`) e afasta o IaC do que seria uma conta de produção real
* Ruim, porque o budget pequeno com encerramento definitivo obriga disciplina de `destroy` e concentra o uso da nuvem em janelas curtas

### Azure for Students (nuvem da fase 2, ADR-025)

* Bom, porque a conta já existe, está validada e tem crédito (~US$ 100/ano sem cartão), com OIDC já configurado desde a fase 2
* Bom, porque o módulo API-Gateway dedica duas aulas ao Azure APIM — há material didático para o gateway nesse provedor
* Ruim, porque a fase 3 exige **serverless + gateway + banco gerenciado integrados**, e o material de Serverless — o módulo que define o desenho integrado function+gateway cobrado — é 100% AWS: entregar em Azure significaria traduzir Lambda→Functions, API Gateway→APIM, SAM→Core Tools por conta própria, sem respaldo do material
* Ruim, porque a subscription de estudante já demonstrou bloqueios severos na fase 2 (adendo do ADR-025: policy de região, allowlist de SKU, quota zero negada) — risco alto de repetir o ciclo de bloqueios com Functions/AKS
* Rejeitada — permanece como histórico da fase 2; os módulos `infra/azure-*` herdados do p2 são removidos deste repo (gap analysis, §4)

### Conta AWS pessoal

* Bom, porque não teria nenhuma das restrições do Learner Lab: IAM livre, sessões sem expiração, qualquer região, backend remoto de state viável
* Ruim, porque o custo sai do próprio bolso — EKS + RDS + NAT somam dezenas de dólares/mês, e um descuido (recurso órfão) vira cobrança real no cartão
* Ruim, porque contraria o princípio já estabelecido no projeto desde o [ADR-019](../fase2/019-pipeline-cicd-deploy.md) de não depender de conta cloud pessoal nem assumir risco financeiro próprio
* Rejeitada

## Consequências

### Positivas

* Alinhamento total com o material didático: o desenho AWS (API Gateway → Lambda → banco) das aulas do módulo Serverless é exatamente o que se entrega, sem tradução entre provedores
* Custo zero pessoal e risco financeiro contido ao budget do Academy
* As restrições do Learner Lab, por serem conhecidas desde já, moldam o desenho (paridade local completa, `destroy` pós-demo, Terraform sem IAM) em vez de surpreender no fim

### Negativas

* Atrito operacional recorrente: secrets de CI re-gravados a cada _Start Lab_; nenhum pipeline que toque a AWS roda sem uma sessão ativa
* Terraform não-idiomático no quesito IAM: `LabRole` fixa em vez de roles mínimas por recurso — uma concessão à conta, documentada, que não seria feita em produção real
* State local do Terraform: sem colaboração concorrente no provisionamento e sem histórico de state — aceitável apenas porque os recursos são efêmeros por natureza
* Budget pequeno com encerramento definitivo: EKS + RDS consomem rápido; a mitigação (desenvolvimento 100% local, nuvem só para validação/demo, `destroy` no runbook) é obrigatória, não opcional

### Neutras

* A conta ainda não foi ativada: até lá, todo o desenvolvimento e a validação acontecem localmente ([ADR-029](029-emulacao-local-lambda.md)); esta decisão destrava o desenho dos repos de infra sem esperar o convite
* A distribuição dos módulos Terraform entre os repos é detalhada nos ADRs de infra: EKS no `p3-infra-k8s` ([ADR-030](030-cluster-kubernetes-eks.md)), RDS no `p3-infra-db` ([ADR-031](031-banco-gerenciado-rds.md)) e API Gateway + functions no próprio `p3-lambda` ([ADR-027](027-api-gateway-aws.md)) — este ADR fixa o provedor e as restrições de conta

## Decisões Relacionadas

- [ADR-025](../fase2/025-ambiente-cloud-demonstracao.md): a nuvem da fase 2 (Azure) era demonstração opcional; esta decisão a substitui como alvo — a fase 3 exige nuvem por enunciado, e o provedor muda para AWS
- [ADR-019](../fase2/019-pipeline-cicd-deploy.md): o princípio "sem conta pessoal, sem risco financeiro próprio" daquele ADR é preservado — o Academy o satisfaz
- [ADR-027](027-api-gateway-aws.md), [ADR-028](028-autenticacao-serverless-cpf.md), [ADR-029](029-emulacao-local-lambda.md): consomem esta decisão — gateway, Lambda e emulação local assumem AWS/us-east-1 e as restrições do Learner Lab

## Notas

* Requisitos citados (RF-025, RF-026, RNF-026, RNF-027) e riscos da conta Academy: [gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md) (tabela de gaps e §5)
* Fichamentos dos módulos da fase 3 no repo `postech-sw-arch-p3-docs`: `docs/superpowers/research/serverless.md` e `docs/superpowers/research/api-gateway.md`
* As restrições do Learner Lab descritas aqui (sessões ~4h, `LabRole`, budget, região) refletem o formato padrão do AWS Academy; valores exatos de budget serão confirmados na ativação da conta e registrados no runbook de sessão

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
