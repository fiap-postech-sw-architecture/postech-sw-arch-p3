# Emulação local da Lambda de autenticação (pytest + AWS SAM CLI)

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

A Lambda de autenticação ([ADR-028](028-autenticacao-serverless-cpf.md)) precisa ser desenvolvida, testada e demonstrada **sem depender da AWS**: a conta AWS Academy tem sessões de ~4h, budget pequeno e nem sequer foi ativada ainda ([ADR-026](026-cloud-alvo-aws-academy.md)) — o gap analysis lista a paridade local completa como mitigação obrigatória dos riscos da conta ([gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md), §5). Além disso, o repo `postech-sw-arch-p3-lambda` nasce sob o mesmo padrão de cobertura do app (≥95%), o que exige testes que rodem em qualquer máquina e no CI.

O material da fase cobre o assunto: o módulo Serverless (fichamento no repo `postech-sw-arch-p3-docs`, `docs/superpowers/research/serverless.md`) dedica a aula 06 ao **AWS SAM CLI** — "permite emular o ambiente da AWS em sua máquina local, o que é útil para depurar e testar o aplicativo antes da implantação", com Docker como pré-requisito — e não menciona LocalStack, serverless-offline nem RIE. O mesmo fichamento registra a ressalva do material: o SAM gera acoplamento com a AWS (apontado duas vezes na aula 06).

O problema: **como testar e emular localmente a Lambda (handler + integração com Postgres + par API Gateway/Lambda) sem AWS, sem duplicar o provisionamento real e sem adotar ferramenta fora do material?**

## Decisão

Adotar **duas camadas de execução local**, com papéis distintos:

1. **Testes pytest, sem qualquer emulação AWS** — a camada que vale para cobertura e CI:
   - **Unit**: os testes invocam o **handler diretamente** como função Python (evento dict + contexto fake), cobrindo validação de CPF, montagem de claims e os caminhos de 401 (RN-022) sem rede nem Docker;
   - **Integração**: os testes sobem **PostgreSQL via testcontainers** e exercitam o fluxo completo handler→banco (consulta por `documento_hash`, cliente ativo/inativo/inexistente, emissão do token) — mesmo padrão de testes de integração já usado no app.
2. **AWS SAM CLI para o dev-loop e a demo local** — `sam local invoke` (uma invocação avulsa) e `sam local start-api` (o par **API Gateway + Lambda** emulado, requer Docker): exatamente a ferramenta ensinada no módulo Serverless (aula 06), usada para depurar o comportamento no runtime real (`python3.13` em container) e para demonstrar a rota de autenticação de ponta a ponta sem AWS ([ADR-027](027-api-gateway-aws.md)).

- **Separação SAM × Terraform, sem duplo deploy.** O **template SAM (`template.yaml`) é versionado no repo `postech-sw-arch-p3-lambda`** e serve a dois propósitos: alimentar a emulação local e **documentar a function** (handler, runtime, memória, timeout, variáveis, rota). O **provisionamento REAL é exclusivamente via Terraform** ([ADR-026](026-cloud-alvo-aws-academy.md); ADR-030, a escrever) — `sam deploy` **não** é usado; o template nunca cria recursos na AWS. Essa fronteira fica registrada aqui para que não surja um segundo caminho de deploy competindo com o IaC oficial.

## Alternativas Consideradas

* pytest (handler direto + testcontainers) + AWS SAM CLI
* LocalStack
* Lambda RIE (Runtime Interface Emulator) puro
* Shim FastAPI próprio em volta do handler

### pytest (handler direto + testcontainers) + AWS SAM CLI

* Bom, porque a camada pytest não depende de emulação nenhuma: handler é função Python, o teste a chama — rápido, determinístico, roda no CI e sustenta a cobertura ≥95%
* Bom, porque testcontainers já é o padrão de integração do app — mesmo Postgres real, mesma disciplina de teste
* Bom, porque o SAM CLI é **a ferramenta do material** (aula 06 do módulo Serverless): dev-loop e demo local usam o que a banca espera ver
* Bom, porque `sam local start-api` emula também o API Gateway, cobrindo o trecho borda→function que o pytest não vê
* Ruim, porque o SAM exige Docker e é mais lento que pytest — mitigado por seu papel ser dev-loop/demo, nunca gate de CI
* Ruim, porque o template SAM introduz um artefato a manter sincronizado com o Terraform — mitigado pela fronteira explícita (SAM só local; Terraform só real) e pelo template dobrar como documentação

### LocalStack

* Bom, porque emula dezenas de serviços AWS (não só Lambda/gateway), útil se o escopo serverless crescesse
* Ruim, porque é significativamente mais pesado (container com a nuvem inteira emulada) para cobrir exatamente dois serviços que o SAM já cobre
* Ruim, porque não é coberto pelo material da fase — adotá-lo abriria mão do respaldo didático sem ganho no escopo atual
* Rejeitada

### Lambda RIE (Runtime Interface Emulator) puro

* Bom, porque é o emulador mínimo oficial: um container com o runtime da Lambda respondendo à Runtime API
* Ruim, porque emula **só o runtime** — não há API Gateway na frente: a rota HTTP, o formato de evento HTTP API e o trecho borda→function ficariam sem cobertura local, exatamente o que `sam local start-api` entrega (o SAM usa RIE por baixo, com o gateway emulado por cima)
* Ruim, porque não aparece no material (o fichamento registra a ausência explicitamente)
* Rejeitada

### Shim FastAPI próprio em volta do handler

* Bom, porque reusaria a stack HTTP que o time domina para expor o handler localmente sem Docker
* Ruim, porque é código próprio a manter (tradução evento HTTP↔dict da Lambda, divergências silenciosas do formato real) para replicar o que o SAM já faz com fidelidade de runtime
* Ruim, porque a demo local deixaria de usar a ferramenta ensinada no material
* Rejeitada

## Consequências

### Positivas

* Desenvolvimento e cobertura da Lambda 100% independentes da AWS — nenhum teste de CI exige sessão do Learner Lab
* O dev-loop e a demo local usam a ferramenta do material (SAM CLI, aula 06), com o runtime real `python3.13` em container — divergências de runtime aparecem localmente, não no deploy
* `sam local start-api` dá a demonstração de ponta a ponta da rota de autenticação (gateway emulado + function + Postgres local) sem custo de nuvem
* O `template.yaml` versionado documenta a function num formato padrão de mercado, além de servir à emulação

### Negativas

* Dois descritores da mesma function (template SAM e Terraform) a manter coerentes — o risco de deriva é aceito e mitigado pela fronteira de papéis (qualquer mudança de configuração real acontece no Terraform; o template segue para manter a emulação fiel)
* SAM CLI + Docker entram como pré-requisitos de dev-loop do repo lambda (o pytest, que é o gate, não os exige)
* A emulação SAM cobre o par gateway+Lambda, não o roteamento completo até o app — limitação de paridade já documentada e aceita no [ADR-027](027-api-gateway-aws.md)

### Neutras

* Se o escopo serverless crescer para outros serviços AWS (filas, buckets), a alternativa LocalStack pode ser reavaliada — nada neste ADR a impede
* A estrutura exata do repo `postech-sw-arch-p3-lambda` (empacotamento, pipeline, gate local) é assunto do bootstrap do repo e dos ADRs de infra; este ADR fixa a estratégia de teste e emulação

## Decisões Relacionadas

- [ADR-028](028-autenticacao-serverless-cpf.md): a function cujos testes e emulação este ADR define
- [ADR-027](027-api-gateway-aws.md): `sam local start-api` é a emulação local do gateway daquele ADR para a rota de autenticação
- [ADR-026](026-cloud-alvo-aws-academy.md): o provisionamento real via Terraform (state local, LabRole, destroy pós-demo) do qual o template SAM é deliberadamente apartado
- [ADR-005](../005-estrategia-testes.md): a estratégia de testes do projeto (pirâmide, testcontainers) que a camada pytest da Lambda estende

## Notas

* Fichamento do módulo Serverless (repo `postech-sw-arch-p3-docs`, `docs/superpowers/research/serverless.md`): SAM CLI com emulação local e Docker como pré-requisito (aula 06); ausência de LocalStack/serverless-offline/RIE no material; ressalva de acoplamento do SAM com a AWS (aula 06, apontada duas vezes)
* Riscos da conta Academy e exigência de paridade local: [gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md), §5
* A cobertura ≥95% herdada do app (`.coveragerc`) vale para o repo lambda desde o primeiro commit — os testes pytest desta decisão são o que a sustenta

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
