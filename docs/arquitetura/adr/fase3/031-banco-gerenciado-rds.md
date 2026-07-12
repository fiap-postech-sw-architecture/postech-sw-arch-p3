# Amazon RDS for PostgreSQL como banco gerenciado da fase 3

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

O Tech Challenge da fase 3 exige **banco de dados gerenciado** ("PostgreSQL, MySQL, SQL Server, etc.") provisionado via **Terraform em repositório próprio**, acompanhado de **justificativa formal da escolha** e **diagrama ER com explicação dos relacionamentos** — ver [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md) e o requisito RNF-027 no [gap analysis](../../../requisitos/fase3/gap-analysis-fase-3.md).

O estado herdado da fase 2: PostgreSQL 16 roda como StatefulSet dentro do cluster ([ADR-017](../fase2/017-provisionamento-banco.md)), com persistência via SQLAlchemy 2.0 em mapeamento imperativo ([ADR-006](../006-mapeamento-imperativo-sqlalchemy.md)), 8 migrações Alembic (`migrations/versions/001..008`) e o diagrama ER em [rfc-001-design-do-sistema.md](../../rfc/rfc-001-design-do-sistema.md). A escolha original do PostgreSQL foi registrada no [ADR-002](../002-banco-postgresql.md), na fase 1. O que muda na fase 3 é o **modo de operação** (gerenciado, fora do cluster) — e o challenge pede que a escolha do banco seja justificada formalmente, o que este ADR também cumpre.

As restrições do ambiente pesam como na decisão do cluster ([ADR-030](030-cluster-kubernetes-eks.md)): AWS Academy com `LabRole` fixa ([ADR-026](026-cloud-alvo-aws-academy.md)), budget pequeno e sessões curtas — o banco gerenciado precisa ser barato, destruível e recriável por `terraform apply`.

**Qual banco de dados gerenciado hospeda os dados do PytStop na fase 3, e como se justifica formalmente a escolha?**

## Decisão

Adotar o **Amazon RDS for PostgreSQL 16**, em **instância mínima** (`db.t3.micro`, single-AZ, sem réplica de leitura), provisionado por **Terraform no repositório `postech-sw-arch-p3-infra-db`** (repositório 3 dos 4 exigidos pelo challenge, com pipeline próprio — [ADR-033](033-cicd-multi-repo.md)).

- **Mesmo engine, nova operação**: PostgreSQL 16 idêntico ao da fase 2 — muda apenas quem opera (RDS em vez de StatefulSet). Nenhuma migração de dados ou de dialeto.
- **Dimensionamento mínimo**: `db.t3.micro`, single-AZ, storage mínimo, sem Multi-AZ nem réplica — suficiente para demo e avaliação; o budget Academy não comporta mais, e o `terraform destroy` pós-demo é parte do runbook.
- **Local permanece Postgres 16 em Docker/kind**: o dev-loop e os testes continuam contra o mesmo engine e versão (docker-compose e kind), preservando a paridade dev/prod que o projeto mantém desde a fase 1.
- **ER atualizado no RFC-003**: o diagrama ER de [rfc-001-design-do-sistema.md](../../rfc/rfc-001-design-do-sistema.md) será atualizado no RFC-003 com os ajustes da fase 3, cumprindo a parte "diagrama ER e explicação dos relacionamentos" do challenge.

## Justificativa formal da escolha do banco

Esta seção é a justificativa formal exigida pelo challenge (RNF-027). A escolha do **modelo relacional** e do **PostgreSQL** se sustenta em quatro argumentos:

1. **O domínio é relacional.** O núcleo do PytStop é uma malha de relacionamentos com integridade referencial obrigatória: cliente ↔ veículo ↔ ordem de serviço ↔ itens (serviços e peças), com estoque e catálogo referenciados pelos itens. O diagrama ER em [rfc-001-design-do-sistema.md](../../rfc/rfc-001-design-do-sistema.md) documenta essas entidades e cardinalidades; consultas do dia a dia (OS por cliente, itens por OS, disponibilidade de peça) são joins naturais, e as invariantes (um veículo pertence a um cliente; um item referencia uma OS existente) são foreign keys, não código de aplicação.

2. **ACID é requisito funcional, não luxo.** As transições de status da ordem de serviço (Recebida → Em diagnóstico → … → Entregue) e o padrão **transactional outbox** ([ADR-022](../fase2/022-transactional-outbox-relay.md)) dependem de transação atômica: a mudança de estado e o evento de integração são gravados no mesmo commit, ou nada é gravado. Um banco sem transações multi-tabela fortes quebraria a garantia central de consistência do sistema.

3. **Continuidade total do investimento da fase 2.** A camada de persistência é SQLAlchemy 2.0 com mapeamento imperativo ([ADR-006](../006-mapeamento-imperativo-sqlalchemy.md)), há 8 migrações Alembic versionadas (`migrations/versions/001..008`) e o domínio de orçamento usa **JSONB** (migração `004`) para estrutura semiestruturada dentro do modelo relacional — um recurso específico do PostgreSQL. Trocar de engine obrigaria a revalidar cada migração e reescrever os pontos JSONB; permanecer no PostgreSQL custa zero retrabalho.

4. **Suporte first-class no serviço gerenciado.** O RDS oferece PostgreSQL 16 como engine de primeira linha (backups automáticos, patching, parameter groups, endpoint TLS), de modo que a exigência "banco gerenciado" do challenge é atendida sem abrir mão de nenhum recurso que o app já usa.

## Alternativas Consideradas

* Amazon RDS for PostgreSQL (instância mínima)
* Amazon RDS for MySQL
* Amazon RDS for SQL Server
* Amazon DynamoDB
* Amazon Aurora Serverless v2 (PostgreSQL)

### Amazon RDS for PostgreSQL (instância mínima)

* Bom, porque preserva 100% do código de persistência, das migrações Alembic e do JSONB da fase 2 — retrabalho zero
* Bom, porque o modelo relacional casa com o domínio e com a exigência do challenge (banco relacional gerenciado + ER + relacionamentos explicados)
* Bom, porque a paridade local é perfeita: o mesmo Postgres 16 roda em Docker/kind no dev-loop
* Ruim, porque single-AZ sem réplica não demonstra alta disponibilidade — aceito: o objetivo é demo com budget Academy, e o upgrade (Multi-AZ, réplica) é mudança de parâmetro Terraform, não de arquitetura

### Amazon RDS for MySQL

* Bom, porque é o engine que o material de monitoramento usa nos exemplos (Zabbix + MySQL — Monitoramento, Aulas 01–02) e é igualmente gerenciado e barato
* Ruim, porque perderia o JSONB (o JSON do MySQL tem semântica e indexação diferentes) e a paridade com todo o código da fase 2 — cada uma das 8 migrações Alembic precisaria ser revalidada contra o dialeto novo
* Ruim, porque não há nenhum ganho compensatório: mesmos custos, mesma categoria de serviço

### Amazon RDS for SQL Server

* Bom, porque está na lista exemplificativa do challenge
* Ruim, porque adiciona custo de licença ao budget Academy e nenhum recurso que o domínio use
* Ruim, porque a distância de dialeto em relação ao código existente é a maior das opções relacionais — retrabalho máximo, ganho zero

### Amazon DynamoDB

* Bom, porque é o banco que o material da fase 3 usa no hands-on de custos (Serverless, Aula 02: POC de agenda de eventos com API Gateway + Lambda + DynamoDB), com modo on-demand barato
* Ruim, porque o domínio do PytStop é relacional — joins, integridade referencial e transições ACID multi-tabela são o caso de uso oposto ao modelo chave-valor/documento do DynamoDB
* Ruim, porque o challenge pede banco **relacional** gerenciado com diagrama ER e explicação de relacionamentos — um banco sem esquema relacional não atende o entregável
* Ruim, porque descartaria SQLAlchemy, Alembic e o outbox transacional ([ADR-022](../fase2/022-transactional-outbox-relay.md)) — reescrita da camada de persistência inteira

### Amazon Aurora Serverless v2 (PostgreSQL)

* Bom, porque é compatível com PostgreSQL (retrabalho de código próximo de zero) e escala a zero de carga — atraente no papel para workload intermitente
* Ruim, porque o custo mínimo por ACU e a complexidade de configuração superam o RDS `db.t3.micro` para o perfil de uso da fase (demo curta, destroy pós-uso) — o budget Academy decide
* Ruim, porque adiciona conceitos (ACUs, scaling policies) sem contrapartida na avaliação — o challenge pede banco gerenciado, não banco serverless

## Consequências

### Positivas

* RNF-027 integralmente coberto: banco gerenciado via Terraform em repo próprio + justificativa formal (esta seção) + ER (RFC-001, atualizado no RFC-003)
* Retrabalho zero na aplicação: mesma URL de conexão via configuração, mesmas migrações, mesmo dialeto — o `alembic upgrade head` roda contra o RDS como rodava contra o StatefulSet
* O banco sai do ciclo de vida do cluster: destruir/recriar o EKS ([ADR-030](030-cluster-kubernetes-eks.md)) não toca o banco, e vice-versa — repos e estados Terraform independentes

### Negativas

* Custo por hora enquanto ligado: como o cluster, o RDS entra no runbook de `terraform destroy` pós-demo; dados de demo são recriados por seed/migração
* Single-AZ sem réplica significa RPO/RTO de demo, não de produção — limitação consciente e documentada
* Conectividade cluster → RDS (security groups, subnets) vira uma costura entre dois repos Terraform, exigindo ordem de provisionamento documentada ([ADR-033](033-cicd-multi-repo.md))

### Neutras

* Parâmetros finos (classe exata, storage, backup window, parameter group) vivem no Terraform do repo `postech-sw-arch-p3-infra-db`, fora deste ADR
* A gestão do segredo de conexão é decidida no [ADR-033](033-cicd-multi-repo.md): variáveis sensíveis via GitHub Secrets/`TF_VAR_*` nos pipelines e via `terraform.tfvars` local (git-ignored) no fluxo manual — Secrets Manager/SSM descartados pelas restrições de IAM/KMS do Learner Lab ([ADR-026](026-cloud-alvo-aws-academy.md))

## Decisões Relacionadas

- [ADR-002](../002-banco-postgresql.md): a escolha original do PostgreSQL (fase 1) — este ADR a reafirma e a eleva a serviço gerenciado
- [ADR-006](../006-mapeamento-imperativo-sqlalchemy.md): o mapeamento imperativo SQLAlchemy que a continuidade de engine preserva
- [ADR-017](../fase2/017-provisionamento-banco.md): o Postgres in-cluster da fase 2, substituído no alvo cloud pelo RDS; a versão local (Docker/kind) permanece
- [ADR-022](../fase2/022-transactional-outbox-relay.md): o outbox transacional cuja atomicidade exige o ACID defendido na justificativa formal
- [ADR-030](030-cluster-kubernetes-eks.md): o cluster que consome este banco; repos e ciclos de vida separados
- [ADR-033](033-cicd-multi-repo.md): pipeline do repo `p3-infra-db` e ordem de deploy (banco antes do cluster/app)

## Notas

* Fonte das evidências de material: fichamentos das disciplinas da fase 3 (Serverless, Aula 02; Monitoramento, Aulas 01–02), em `postech-sw-arch-p3-docs/docs/superpowers/research/`
* Requisito formal: RNF-027 ([gap-analysis-fase-3.md](../../../requisitos/fase3/gap-analysis-fase-3.md)); exigência original em [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md)
* O diagrama ER vigente está em [rfc-001-design-do-sistema.md](../../rfc/rfc-001-design-do-sistema.md); os ajustes da fase 3 serão registrados no RFC-003

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
