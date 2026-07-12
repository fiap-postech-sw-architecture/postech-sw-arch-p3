# API Gateway da fase 3: Amazon API Gateway (HTTP API)

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

O RF-026 exige um API Gateway protegendo as rotas sensíveis, com controle de acesso e roteamento ([gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md)). Hoje não há gateway: as rotas protegidas são resolvidas dentro do próprio app, via dependência `obter_usuario_atual` (`src/autenticacao/interfaces/middleware.py:28`) e RBAC `exigir_papel` (`src/autenticacao/interfaces/middleware.py`).

O material da fase aponta caminhos distintos. O módulo API-Gateway (fichamento no repo `postech-sw-arch-p3-docs`, `docs/superpowers/research/api-gateway.md`) não menciona AWS em nenhuma aula: divide-se entre Azure APIM (aulas 02–03) e **Kong open source via Docker Compose** (aulas 04–06), com proteção por consumers + plugins de API Key/basic auth. Já o módulo Serverless (fichamento em `docs/superpowers/research/serverless.md`, mesmo repo) usa o **Amazon API Gateway** como peça central: "por si só a Lambda não é capaz de expor uma API RESTful, será preciso uma API Gateway" (aula 02), apresenta os três tipos: HTTP API (leve, barata, ideal para serverless), REST API e WebSocket (aulas 02/04); e apresenta o gateway exigindo autenticação JWT na frente do serviço (aula 05).

Como a fase 3 exige uma function serverless de autenticação integrada ao gateway (RF-025 + RN-021) e a cloud alvo é AWS ([ADR-026](026-cloud-alvo-aws-academy.md)), o problema é: **qual gateway usar: o serviço gerenciado da AWS, que integra nativamente com a Lambda, ou um gateway auto-hospedado (Kong/Traefik) rodando junto ao cluster?**

## Decisão

Adotar o **Amazon API Gateway, no modo HTTP API**, como o gateway da fase 3:

- **HTTP API, não REST API.** É o modo que o próprio material recomenda para serverless/microsserviços: mais leve e mais barato (aulas 02/04 do módulo Serverless); os recursos extras do modo REST (API keys por cliente, WAF, endpoints privados) não são exigidos pelo challenge.
- **Lambda authorizer nas rotas sensíveis.** O gateway valida o JWT ([ADR-028](028-autenticacao-serverless-cpf.md)) via Lambda authorizer antes de rotear ao backend; rotas públicas (health check, acompanhamento público) passam sem authorizer. O módulo Serverless demonstra o padrão de gateway exigindo JWT (aula 05, com Cognito como emissor); aqui o authorizer é uma Lambda própria porque o emissor do token de cliente é a nossa function (RF-025), não um user pool.
- **Validação JWT redundante mantida no app** (_defense in depth_ + paridade local). O app continua validando o token em `obter_usuario_atual` mesmo atrás do gateway: (1) o gateway deixa de ser ponto único de falha de segurança — um erro de configuração de rota não expõe endpoint sem autenticação; (2) o ambiente local (kind), que não tem o gateway na frente, mantém exatamente o mesmo comportamento de segurança do ambiente cloud.
- **Provisionamento via Terraform** no repo `postech-sw-arch-p3-lambda`: o gateway, as rotas, o authorizer e as functions formam uma unidade de deploy única, provisionada pelo Terraform desse repo e publicada pelo seu `cd.yml` ([ADR-033](033-cicd-multi-repo.md)); restrições do Learner Lab ([ADR-026](026-cloud-alvo-aws-academy.md)): região `us-east-1`, `LabRole`, `destroy` pós-demo.
- **Emulação local pelo SAM CLI.** `sam local start-api` ([ADR-029](029-emulacao-local-lambda.md)) emula o par API Gateway + Lambda para a rota de autenticação, exatamente a ferramenta do módulo Serverless (aula 06). As rotas do app, localmente, ficam **expostas direto no kind, sem gateway na frente**: paridade parcial, documentada e aceita; a validação JWT redundante no app garante que a semântica de segurança seja a mesma nos dois ambientes.

## Alternativas Consideradas

* Amazon API Gateway (HTTP API)
* Kong self-hosted no cluster
* Traefik

### Amazon API Gateway (HTTP API)

* Bom, porque integra **nativamente** com a Lambda de autenticação exigida pelo RF-025: trigger e authorizer são recursos de primeira classe, sem plugin nem credencial intermediária
* Bom, porque é exatamente o desenho do material do módulo Serverless: API Gateway na frente da Lambda (aula 02) e gateway exigindo JWT na frente do serviço (aula 05)
* Bom, porque o custo é coberto pelo budget do Academy e o serviço é totalmente gerenciado — nada para operar dentro do cluster
* Bom, porque é provisionável via Terraform, atendendo o RNF-026 (gateway como IaC)
* Ruim, porque não roda localmente por inteiro: a emulação via SAM cobre gateway+Lambda, mas o roteamento completo (gateway → app no cluster) só existe na AWS — paridade parcial aceita
* Ruim, porque acopla a borda ao provedor AWS (trade-off já assumido no [ADR-026](026-cloud-alvo-aws-academy.md))

### Kong self-hosted no cluster

* Bom, porque é a rota que o módulo API-Gateway ensina de ponta a ponta (aulas 04–06: Kong + banco + Konga via Docker Compose, consumers, plugins de autenticação) — forte para rodar 100% local
* Bom, porque é open source e agnóstico de provedor
* Ruim, porque adiciona um componente operacional dentro do cluster (Kong + banco próprio + GUI), com upgrade, backup e monitoramento por nossa conta — no Learner Lab, onde tudo é destruído e reerguido por sessão, cada peça a mais custa tempo de sessão
* Ruim, porque a integração com a Lambda de autenticação exigiria o plugin `aws-lambda` do Kong configurado com credenciais AWS **dentro do cluster** — credenciais que no Academy são temporárias e trocam a cada ~4h ([ADR-026](026-cloud-alvo-aws-academy.md)), tornando a integração frágil por construção
* Rejeitada para a nuvem; o material de Kong permanece como referência conceitual (consumers, rotas, políticas na borda)

### Traefik

* Bom, porque é leve e popular como ingress/gateway em Kubernetes
* Ruim, porque é apenas citado no enunciado do challenge como opção, **sem nenhum material de aula** — nem o módulo API-Gateway nem o Serverless o cobrem; adotá-lo significaria abrir mão do respaldo didático das duas rotas ensinadas
* Ruim, porque compartilha as desvantagens operacionais do self-hosted (componente no cluster) sem a vantagem do Kong de ter sido ensinado
* Rejeitada

## Consequências

### Positivas

* Integração direta gateway ↔ Lambda de autenticação, sem credenciais intermediárias nem plugins — o desenho do RF-025/RF-026 fica com o mínimo de peças
* Defense in depth: gateway valida na borda, app revalida por dentro — nenhum dos dois é ponto único de falha de autenticação
* Paridade de comportamento de segurança entre local e cloud garantida pela validação redundante no app, mesmo sem gateway local na frente do kind
* Gateway 100% Terraform (RNF-026), sem operação de componente adicional no cluster

### Negativas

* Paridade local **parcial**: `sam local start-api` cobre apenas a rota de autenticação; o roteamento gateway→app não existe no ambiente local — testes desse trecho só na AWS, dentro de sessões do Learner Lab
* A validação redundante custa uma verificação de assinatura JWT a mais por requisição no app — custo desprezível frente ao ganho de segurança e paridade
* Configuração de rotas duplicada conceitualmente (rotas no gateway + rotas no app); mitigada por o gateway rotear por prefixo, sem reescrever caminhos

### Neutras

* A escolha HTTP API vs REST API pode ser revista se o challenge exigir recurso exclusivo do modo REST (throttling por cliente, WAF) — a migração é de recurso Terraform, não de desenho
* O detalhamento do roteamento (prefixos por contexto, integração com o cluster [ADR-030](030-cluster-kubernetes-eks.md)) fica para o RFC-003; este ADR fixa a tecnologia, o modelo de autorização e o repo dono do Terraform do gateway (`p3-lambda`)

## Decisões Relacionadas

- [ADR-026](026-cloud-alvo-aws-academy.md): a cloud alvo AWS e as restrições do Learner Lab são a premissa desta escolha — e o motivo direto da rejeição do Kong (credenciais rotativas no cluster)
- [ADR-028](028-autenticacao-serverless-cpf.md): define a Lambda que emite o JWT validado pelo authorizer deste gateway
- [ADR-029](029-emulacao-local-lambda.md): define a emulação local (`sam local start-api`) que cobre a rota de autenticação deste gateway
- [ADR-004](../004-autenticacao-jwt.md): a validação JWT do app decidida lá permanece — agora como camada redundante atrás do gateway

## Notas

* Fichamentos citados, no repo `postech-sw-arch-p3-docs`: `docs/superpowers/research/serverless.md` (aulas 02, 04, 05, 06) e `docs/superpowers/research/api-gateway.md` (aulas 04–06, Kong)
* RF-026, RN-021 e o estado atual da proteção de rotas no app: [gap analysis da fase 3](../../../requisitos/fase3/gap-analysis-fase-3.md)
## Adendo (2026-07-11) — paridade local do gateway deixa de ser parcial

O `sam local start-api` (SAM CLI >= 1.80) suporta Lambda authorizer, detalhe ausente do material da disciplina e não verificado quando este ADR aceitou a paridade local "parcial" (roteamento e authorizer sem emulação). Com isso, a rota protegida do gateway também é demonstrável localmente; comportamento provado ao vivo no gateway emulado: 401 sem token, 403 com token adulterado (deny do authorizer), e o token válido alcança o handler (o par discriminante 401×403 do HTTP API). O desenho de produção não muda; muda o alcance da demo sem AWS. Detalhes e reavaliação do LocalStack no [Adendo do ADR-029](029-emulacao-local-lambda.md#adendo-2026-07-11--authorizer-local-via-sam-e-reavaliação-do-localstack).

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
