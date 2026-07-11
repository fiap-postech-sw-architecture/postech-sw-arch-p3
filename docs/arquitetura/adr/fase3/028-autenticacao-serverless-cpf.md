# Autenticação serverless de clientes por CPF (Lambda Python)

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

O RF-025 exige uma function serverless de autenticação que valide o CPF do cliente, consulte sua existência e status na base e emita um JWT; a RN-021 exige que o token emitido pela function seja o aceito pelas APIs protegidas; a RN-022 exige que CPF inexistente ou cliente inativo **não** receba token ([gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md)).

O que já existe no app (snapshot do p2):

- Emissão e validação de JWT HS256 no contexto `autenticacao` (`src/autenticacao/infraestrutura/jwt_service.py`), para **usuários internos** (admin/atendente/mecânico), com claims `sub`/`email`/`papel`/`jti` e segredo `JWT_SECRET`.
- Consulta de cliente por documento via `documento_hash` (`src/cliente_veiculo/infraestrutura/repository.py:69-73`) — o CPF não é armazenado em claro; a busca é por hash determinístico.
- Invariante de cliente ativo no domínio (`src/cliente_veiculo/dominio/cliente.py`).
- Validação de CPF/CNPJ com **brutils** ([ADR-010](../010-validacao-documentos-brutils.md)).

O que não existe: qualquer fluxo CPF→token, e qualquer function serverless. O challenge adiciona um **segundo público** — clientes autenticando por CPF na borda — que precisa conviver com o público interno sem quebrar o validador atual. O problema: **como desenhar a function (runtime, repo, lógica, emissão) para cumprir RF-025/RN-021/RN-022 mantendo compatibilidade com o validador JWT do app?**

## Decisão

Criar uma **Lambda em Python, no repo `postech-sw-arch-p3-lambda`**, como a function de autenticação de clientes:

- **Runtime `python3.13`.** O runtime gerenciado mais recente disponível no Lambda — Python 3.14 **não** está disponível como runtime gerenciado (o fichamento do módulo Serverless, repo `postech-sw-arch-p3-docs`, `docs/superpowers/research/serverless.md`, já antecipava que runtimes gerenciados atrasam em relação ao release). O app continua em 3.14; a divergência é aceitável porque a Lambda não importa código do app — compartilha apenas contratos (formato do hash de documento, claims do token).
- **Lógica do handler**, em ordem:
  1. Valida o **formato** do CPF com **brutils** — a mesma lib do app ([ADR-010](../010-validacao-documentos-brutils.md)), garantindo que Lambda e app aceitem/rejeitem os mesmos documentos;
  2. Consulta o cliente por documento no banco, pela **mesma estratégia `documento_hash`** do app (`src/cliente_veiculo/infraestrutura/repository.py:69-73`) — mesmo algoritmo de hash, mesma coluna;
  3. Cliente **inexistente ou inativo** → **401 sem token** (RN-022); a resposta não distingue os dois casos, para não vazar existência de CPF;
  4. Cliente ativo → emite **JWT HS256** assinado com o **segredo compartilhado `JWT_SECRET`** (o mesmo do app), com claims **compatíveis com o validador do app** (`src/autenticacao/infraestrutura/jwt_service.py`) e a claim **`papel="cliente"`**, papel novo que o RBAC do app passa a reconhecer.
- **Dois emissores, públicos disjuntos.** O app **continua** emitindo tokens para usuários internos (admin/atendente/mecânico) pelo fluxo de login atual; a Lambda é o **único emissor para clientes** (RN-021). Não há sobreposição: nenhum papel é emitido pelos dois lados, então não existe ambiguidade de origem por papel.
- **Um único segredo e um único validador.** HS256 com `JWT_SECRET` compartilhado significa que o validador existente do app (e o Lambda authorizer do gateway, [ADR-027](027-api-gateway-aws.md)) valida tokens de ambos os emissores sem mudança de algoritmo. A gestão do segredo compartilhado segue o [ADR-033](033-cicd-multi-repo.md) (GitHub Secrets/`TF_VAR_*`; Secrets Manager/SSM descartados pelas restrições de IAM/KMS do Learner Lab) e as restrições da conta ([ADR-026](026-cloud-alvo-aws-academy.md)) e é detalhada na infra.

## Alternativas Consideradas

* Lambda Python própria consultando a base e emitindo o JWT
* Amazon Cognito user pool como emissor
* Segundo segredo ou par de chaves (JWKS/RS256) para a Lambda

### Lambda Python própria consultando a base e emitindo o JWT

* Bom, porque é literalmente o que o challenge pede: a **própria function** valida o CPF, consulta existência e status na **nossa base** e emite o token (RF-025) — nenhum serviço intermediário cumpre isso por nós
* Bom, porque Python mantém a stack homogênea (o fichamento do módulo Serverless registra Python entre as linguagens suportadas pelo Lambda, aula 06) e permite reusar brutils e a estratégia `documento_hash` por contrato
* Bom, porque HS256 + `JWT_SECRET` compartilhado torna o token indistinguível para o validador do app — a RN-021 é satisfeita por construção
* Ruim, porque a Lambda acessa o banco diretamente, criando um segundo cliente do schema fora do app — mitigado por o acesso ser somente leitura, restrito à consulta de cliente por hash
* Ruim, porque runtime 3.13 ≠ app 3.14 — aceitável porque não há código compartilhado, só contratos

### Amazon Cognito user pool como emissor

* Bom, porque é o desenho do material (aula 05 do módulo Serverless: user pool emite JWT, API Gateway valida), gerenciado e sem código próprio de emissão
* Ruim, porque o challenge exige que a **própria function** valide CPF + status **na nossa base** e emita o token — o Cognito autentica contra o **seu próprio** diretório de usuários e não consulta nossa base de clientes; encaixá-lo exigiria sincronizar clientes para o user pool ou triggers customizados, invertendo a exigência do enunciado
* Ruim, porque os tokens do Cognito são RS256 com claims próprias — o validador HS256 do app não os aceita sem reescrita (quebraria a RN-021 ou forçaria dois validadores)
* Rejeitada

### Segundo segredo ou par de chaves (JWKS/RS256) para a Lambda

* Bom, porque isolaria o comprometimento de um emissor do outro e aproximaria o desenho de um IdP de mercado (chave pública para validar, privada para assinar)
* Ruim, porque exigiria o validador do app (e o authorizer) a lidar com múltiplas chaves/algoritmos e a expor/distribuir JWKS — complexidade real sem ganho no escopo: os dois emissores pertencem ao mesmo sistema e ao mesmo time, e o segredo já é gerenciado como secret de infraestrutura
* Rejeitada — fica como evolução natural se os emissores um dia pertencerem a domínios de confiança distintos

## Consequências

### Positivas

* RF-025, RN-021 e RN-022 cobertos com o mínimo de peças: uma Lambda, o segredo já existente e o validador já existente
* Paridade de regras entre borda e app: mesma lib de validação de CPF (brutils), mesma estratégia de busca (`documento_hash`) — um documento aceito na Lambda é o mesmo aceito no app
* O papel `cliente` entra no RBAC existente do app como mais um papel — sem fluxo paralelo de autorização

### Negativas

* Segredo compartilhado entre app e Lambda: a rotação de `JWT_SECRET` passa a envolver dois componentes em repos distintos — documentada no runbook; o raio de comprometimento é o mesmo de hoje (um segredo, um sistema)
* A Lambda depende do banco estar acessível a partir da AWS (rede/latência) — no ambiente do Learner Lab isso significa provisionar banco e function na mesma janela de sessão ([ADR-026](026-cloud-alvo-aws-academy.md))
* Duplicação de contrato (hash de documento, claims) entre repos sem código compartilhado: mudanças nesses contratos exigem alteração coordenada — mitigada por testes de integração na Lambda que validam o token contra as claims esperadas pelo app ([ADR-029](029-emulacao-local-lambda.md))

### Neutras

* O acompanhamento público por placa+documento existente (`router_publico.py`) não é alterado por este ADR; sua eventual absorção pelas rotas autenticadas de cliente é decisão do RFC de design da fase 3 (gap analysis, §2)
* Empacotamento, template SAM e pipeline do repo `postech-sw-arch-p3-lambda` são detalhados no [ADR-029](029-emulacao-local-lambda.md) e nos ADRs de infra

## Decisões Relacionadas

- [ADR-027](027-api-gateway-aws.md): o gateway roteia a rota de autenticação para esta Lambda e usa o token dela no authorizer das rotas sensíveis
- [ADR-029](029-emulacao-local-lambda.md): define como esta Lambda é testada e emulada localmente, sem AWS
- [ADR-026](026-cloud-alvo-aws-academy.md): restrições da conta (LabRole, sessões, região) que o deploy desta Lambda herda
- [ADR-004](../004-autenticacao-jwt.md): o esquema JWT HS256 do app, cujo validador esta Lambda passa a alimentar
- [ADR-010](../010-validacao-documentos-brutils.md): a lib de validação de documentos reusada no handler

## Notas

* Evidências do estado atual (emissão/validação JWT, `documento_hash`, invariante de ativo) e requisitos RF-025/RN-021/RN-022: [gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md), tabela de gaps e §2
* Fichamento do módulo Serverless (repo `postech-sw-arch-p3-docs`, `docs/superpowers/research/serverless.md`): Python entre as linguagens suportadas (aula 06); Cognito user pool como emissor JWT no desenho do material (aula 05); alerta sobre atraso de runtimes gerenciados frente ao release do Python

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
