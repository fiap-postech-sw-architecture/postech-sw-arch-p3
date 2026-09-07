# Private Gateway–EKS Integration Implementation Plan

> [↑ Raiz do projeto](../../../README.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o proxy HTTP público entre o API Gateway e o app no EKS por
VPC Link e NLB interno, sem criar VPC, NAT Gateway ou IAM.

**Architecture:** O Terraform do EKS cria duas subnets privadas na VPC default.
O overlay do app cria um NLB interno nessas subnets. O Terraform da Lambda
descobre as subnets por tag, recebe o ARN do listener do NLB e cria o VPC Link e
uma integração privada compartilhada pelas duas rotas de cliente.

**Tech Stack:** Terraform 1.10+, AWS provider 5.x, Amazon EKS 1.34, Kubernetes,
Kustomize, API Gateway HTTP API, AWS Lambda, GitHub Actions, pytest e PyYAML.

---

## Mapa de arquivos

### `postech-sw-arch-p3-infra-k8s`

- Criar `network.tf`: subnets privadas, route table e associações.
- Criar `tests/network.tftest.hcl`: contrato da rede privada.
- Modificar `Makefile`: incluir `terraform test` no gate.
- Modificar `outputs.tf`: expor IDs das subnets para validação operacional.
- Modificar `README.md` e `MEMORY.md`: documentar rede e custo.

### `postech-sw-arch-p3`

- Criar `tests/unitarios/test_eks_overlay.py`: contrato do NLB e smoke privado.
- Modificar `k8s/overlays/eks/patch-api-service.yaml`: NLB interno e cross-zone.
- Modificar `k8s/overlays/eks/kustomization.yaml`: remover descrição pública.
- Modificar `.github/workflows/cd.yml`: smoke via `kubectl port-forward`.
- Modificar `README.md` e `MEMORY.md`: marcar o transporte como implementado.

### `postech-sw-arch-p3-lambda`

- Criar `terraform/tests/vpc_link.tftest.hcl`: contrato da integração privada.
- Modificar `terraform/variables.tf`: trocar URL por ARN do listener.
- Modificar `terraform/main.tf`: subnet discovery, security group, VPC Link e
  integração privada.
- Modificar `terraform/terraform.tfvars.example`: novo contrato de entrada.
- Modificar `.github/workflows/cd.yml`: renomear o secret do listener.
- Modificar `Makefile`: incluir `terraform test` no gate.
- Modificar `README.md` e `MEMORY.md`: operação e decisão final.

### `postech-sw-arch-p3-docs`

- Modificar `docs/runbooks/aws-academy-setup.md`: ordem de criação, validação e
  desmontagem.
- Modificar `docs/runbooks/proximas-etapas.md`: remover dependência de URL
  pública.
- Modificar `MEMORY.md`: registrar o contrato operacional, se aplicável.

## Task 1: Criar a rede privada no Terraform do EKS

**Files:**

- Create: `postech-sw-arch-p3-infra-k8s/network.tf`
- Create: `postech-sw-arch-p3-infra-k8s/tests/network.tftest.hcl`
- Modify: `postech-sw-arch-p3-infra-k8s/Makefile`
- Modify: `postech-sw-arch-p3-infra-k8s/outputs.tf`
- Modify: `postech-sw-arch-p3-infra-k8s/README.md`
- Modify: `postech-sw-arch-p3-infra-k8s/MEMORY.md`

- [ ] **Step 1: Escrever o teste Terraform da rede**

Criar `tests/network.tftest.hcl`:

```hcl
mock_provider "aws" {}

run "private_network" {
  command = plan

  assert {
    condition     = length(aws_subnet.private) == 2
    error_message = "A integração privada exige exatamente duas subnets."
  }

  assert {
    condition = (
      aws_subnet.private["us-east-1a"].cidr_block == "172.31.240.0/24" &&
      aws_subnet.private["us-east-1b"].cidr_block == "172.31.241.0/24"
    )
    error_message = "Os CIDRs devem corresponder ao inventário aprovado."
  }

  assert {
    condition = alltrue([
      for subnet in aws_subnet.private : !subnet.map_public_ip_on_launch
    ])
    error_message = "Subnets privadas não podem atribuir IP público."
  }

  assert {
    condition     = length(aws_route_table_association.private) == 2
    error_message = "Cada subnet privada deve usar a route table sem rota default."
  }
}
```

- [ ] **Step 2: Executar o teste e confirmar a falha**

Run:

```bash
terraform init -backend=false
terraform test
```

Expected: FAIL porque `aws_subnet.private` e
`aws_route_table_association.private` ainda não existem.

- [ ] **Step 3: Implementar a rede mínima**

Criar `network.tf`:

```hcl
locals {
  private_subnet_cidrs = {
    us-east-1a = "172.31.240.0/24"
    us-east-1b = "172.31.241.0/24"
  }
}

resource "aws_subnet" "private" {
  for_each = local.private_subnet_cidrs

  vpc_id                  = data.aws_vpc.default.id
  availability_zone       = each.key
  cidr_block              = each.value
  map_public_ip_on_launch = false

  tags = {
    Name                                      = "${var.cluster_name}-private-${each.key}"
    "kubernetes.io/role/internal-elb"         = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

resource "aws_route_table" "private" {
  vpc_id = data.aws_vpc.default.id

  tags = {
    Name = "${var.cluster_name}-private"
  }
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private.id
}
```

Não adicionar bloco `route`, Internet Gateway ou NAT Gateway.

- [ ] **Step 4: Expor os IDs para validação**

Adicionar a `outputs.tf`:

```hcl
output "private_subnet_ids" {
  description = "Subnets privadas usadas pelo NLB interno e pelo VPC Link."
  value       = [for subnet in aws_subnet.private : subnet.id]
}
```

- [ ] **Step 5: Incluir o teste no gate**

Em `Makefile`, adicionar `test` ao `.PHONY` e usar:

```make
test: init ## Valida contratos Terraform com provider mockado
	terraform test

gate: fmt-check validate test ## Gate local = fmt-check + validate + test
```

Atualizar os textos de `apply` e `destroy` para a janela de gravação, sem
alterar o comportamento dos alvos.

- [ ] **Step 6: Rodar o gate do EKS**

Run: `make gate`

Expected: formatação válida, `terraform validate` com `Success!` e
`terraform test` com `1 passed, 0 failed`.

- [ ] **Step 7: Atualizar README e MEMORY**

Documentar os dois CIDRs, ausência de rota default/NAT, tags de descoberta,
output `private_subnet_ids` e uso exclusivo por NLB/VPC Link. Registrar a
decisão no topo de `MEMORY.md`, sem editar entradas antigas.

- [ ] **Step 8: Commitar o módulo EKS**

```bash
git add network.tf tests/network.tftest.hcl Makefile outputs.tf README.md MEMORY.md
git commit -m "feat: adiciona rede privada para integração"
```

## Task 2: Publicar a API por NLB interno

**Files:**

- Create: `postech-sw-arch-p3/tests/unitarios/test_eks_overlay.py`
- Modify: `postech-sw-arch-p3/k8s/overlays/eks/patch-api-service.yaml`
- Modify: `postech-sw-arch-p3/k8s/overlays/eks/kustomization.yaml`
- Modify: `postech-sw-arch-p3/.github/workflows/cd.yml`
- Modify: `postech-sw-arch-p3/README.md`
- Modify: `postech-sw-arch-p3/MEMORY.md`

- [ ] **Step 1: Escrever os testes do overlay e do smoke**

Criar `tests/unitarios/test_eks_overlay.py`:

```python
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


def test_overlay_eks_usa_nlb_interno() -> None:
    patch = yaml.safe_load(
        (ROOT / "k8s/overlays/eks/patch-api-service.yaml").read_text()
    )
    annotations = patch["metadata"]["annotations"]

    assert annotations["service.beta.kubernetes.io/aws-load-balancer-type"] == "nlb"
    assert annotations["service.beta.kubernetes.io/aws-load-balancer-internal"] == "true"
    assert (
        annotations[
            "service.beta.kubernetes.io/"
            "aws-load-balancer-cross-zone-load-balancing-enabled"
        ]
        == "true"
    )
    assert patch["spec"]["type"] == "LoadBalancer"


def test_cd_valida_api_por_port_forward() -> None:
    workflow = (ROOT / ".github/workflows/cd.yml").read_text()

    assert "port-forward service/pytstop-api 18000:8000" in workflow
    assert "http://127.0.0.1:18000/api/v1/saude" in workflow
    assert "status.loadBalancer.ingress" not in workflow
```

- [ ] **Step 2: Executar os testes e confirmar a falha**

Run:

```bash
uv run --no-sync pytest -q tests/unitarios/test_eks_overlay.py
```

Expected: FAIL porque as annotations e o port-forward ainda não existem.

- [ ] **Step 3: Configurar o Service**

Substituir `patch-api-service.yaml` por:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: pytstop-api
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
```

Atualizar os comentários de `kustomization.yaml` para descrever NLB interno e
VPC Link, sem afirmar que o endereço é público.

- [ ] **Step 4: Trocar o smoke externo por port-forward**

Em `.github/workflows/cd.yml`, substituir o passo que consulta
`.status.loadBalancer.ingress` por:

```yaml
- name: Smoke test (port-forward)
  run: |
    kubectl -n pytstop port-forward service/pytstop-api 18000:8000 \
      >/tmp/pytstop-api-port-forward.log 2>&1 &
    port_forward_pid=$!
    trap 'kill "$port_forward_pid" 2>/dev/null || true' EXIT

    for _ in {1..30}; do
      if curl --fail --silent \
        http://127.0.0.1:18000/api/v1/saude >/dev/null; then
        exit 0
      fi
      sleep 2
    done

    cat /tmp/pytstop-api-port-forward.log
    exit 1
```

- [ ] **Step 5: Executar os testes e renderizar o overlay**

Run:

```bash
uv run --no-sync pytest -q tests/unitarios/test_eks_overlay.py
kubectl kustomize --load-restrictor=LoadRestrictionsNone k8s/overlays/eks
```

Expected: 2 testes passando e Service renderizado com as três annotations.

- [ ] **Step 6: Atualizar README e MEMORY**

Remover a marcação de “desenho aprovado” do README, pois o transporte estará
implementado. Registrar o NLB interno e o smoke por port-forward no topo do
`MEMORY.md`, sem duplicar a justificativa da spec.

- [ ] **Step 7: Rodar o gate do app**

Run: `make check`

Expected: lint, formatação, tipos, segurança e testes verdes com cobertura
mínima de 95%.

- [ ] **Step 8: Commitar app e pipeline**

```bash
git add tests/unitarios/test_eks_overlay.py k8s/overlays/eks/patch-api-service.yaml \
  k8s/overlays/eks/kustomization.yaml .github/workflows/cd.yml README.md MEMORY.md
git commit -m "feat: publica API em NLB interno"
```

## Task 3: Criar o VPC Link no Terraform da Lambda

**Files:**

- Create: `postech-sw-arch-p3-lambda/terraform/tests/vpc_link.tftest.hcl`
- Modify: `postech-sw-arch-p3-lambda/terraform/variables.tf`
- Modify: `postech-sw-arch-p3-lambda/terraform/main.tf`
- Modify: `postech-sw-arch-p3-lambda/terraform/terraform.tfvars.example`
- Modify: `postech-sw-arch-p3-lambda/.github/workflows/cd.yml`
- Modify: `postech-sw-arch-p3-lambda/Makefile`
- Modify: `postech-sw-arch-p3-lambda/README.md`
- Modify: `postech-sw-arch-p3-lambda/MEMORY.md`

- [ ] **Step 1: Escrever o teste da integração privada**

Criar `terraform/tests/vpc_link.tftest.hcl`:

```hcl
mock_provider "aws" {}
mock_provider "archive" {}

variables {
  jwt_secret       = "01234567890123456789012345678901"
  encryption_key   = "01234567890123456789012345678901"
  database_url     = "postgresql://user:pass@db.internal:5432/pytstop"
  app_listener_arn = "arn:aws:elasticloadbalancing:us-east-1:924563550535:listener/net/pytstop/0000000000000000/1111111111111111"
}

run "private_proxy" {
  command = plan

  override_data {
    target = data.aws_caller_identity.current
    values = { account_id = "924563550535" }
  }

  override_data {
    target = data.aws_vpc.default
    values = { id = "vpc-00000000000000000", cidr_block = "172.31.0.0/16" }
  }

  override_data {
    target = data.aws_subnets.default
    values = { ids = ["subnet-public"] }
  }

  override_data {
    target = data.aws_subnets.private
    values = { ids = ["subnet-private-a", "subnet-private-b"] }
  }

  assert {
    condition     = aws_apigatewayv2_integration.minhas_ordens.connection_type == "VPC_LINK"
    error_message = "As rotas de cliente devem usar VPC Link."
  }

  assert {
    condition     = aws_apigatewayv2_integration.minhas_ordens.integration_uri == var.app_listener_arn
    error_message = "A integração deve apontar para o listener do NLB."
  }

  assert {
    condition = (
      aws_apigatewayv2_integration.minhas_ordens.request_parameters["overwrite:path"]
      == "$request.path"
    )
    error_message = "O prefixo do stage deve ser removido antes do FastAPI."
  }

  assert {
    condition = (
      aws_vpc_security_group_egress_rule.vpc_link_app.from_port == 8000 &&
      aws_vpc_security_group_egress_rule.vpc_link_app.to_port == 8000
    )
    error_message = "O VPC Link deve sair somente pela porta da API."
  }
}
```

- [ ] **Step 2: Executar o teste e confirmar a falha**

Run:

```bash
terraform -chdir=terraform init -backend=false -input=false
terraform -chdir=terraform test
```

Expected: FAIL porque `app_listener_arn`, `data.aws_subnets.private`, o VPC Link
e a integração `minhas_ordens` ainda não existem.

- [ ] **Step 3: Trocar a variável pública pelo listener ARN**

Substituir `app_base_url` em `terraform/variables.tf`:

```hcl
variable "app_listener_arn" {
  description = "ARN do listener TCP 8000 do NLB interno da aplicação"
  type        = string

  validation {
    condition = can(regex(
      "^arn:aws:elasticloadbalancing:us-east-1:[0-9]{12}:listener/net/.+$",
      var.app_listener_arn,
    ))
    error_message = "app_listener_arn deve ser um ARN de listener NLB em us-east-1."
  }
}
```

- [ ] **Step 4: Descobrir as subnets privadas e criar o security group**

Adicionar após `data.aws_subnets.default` em `terraform/main.tf`:

```hcl
data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "tag:kubernetes.io/role/internal-elb"
    values = ["1"]
  }
}

resource "aws_security_group" "vpc_link" {
  name        = "pytstop-vpc-link"
  description = "Saida do VPC Link para a API no NLB interno"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_egress_rule" "vpc_link_app" {
  security_group_id = aws_security_group.vpc_link.id
  description       = "API PytStop na VPC default"
  from_port         = 8000
  to_port           = 8000
  ip_protocol       = "tcp"
  cidr_ipv4         = data.aws_vpc.default.cidr_block
}
```

- [ ] **Step 5: Criar o VPC Link**

Adicionar antes das integrações HTTP:

```hcl
resource "aws_apigatewayv2_vpc_link" "app" {
  name               = "pytstop-app"
  security_group_ids = [aws_security_group.vpc_link.id]
  subnet_ids         = data.aws_subnets.private.ids

  lifecycle {
    precondition {
      condition     = length(data.aws_subnets.private.ids) == 2
      error_message = "A VPC deve conter as duas subnets privadas do PytStop."
    }
  }
}
```

- [ ] **Step 6: Substituir as duas integrações públicas por uma privada**

Remover `aws_apigatewayv2_integration.listar_minhas_ordens` e
`aws_apigatewayv2_integration.obter_minha_ordem`. Criar:

```hcl
resource "aws_apigatewayv2_integration" "minhas_ordens" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "GET"
  integration_uri        = var.app_listener_arn
  connection_type        = "VPC_LINK"
  connection_id          = aws_apigatewayv2_vpc_link.app.id
  payload_format_version = "1.0"

  request_parameters = {
    "overwrite:path" = "$request.path"
  }
}
```

Nas duas rotas, usar:

```hcl
target = "integrations/${aws_apigatewayv2_integration.minhas_ordens.id}"
```

Não alterar o authorizer, `POST /auth` ou a configuração VPC da Lambda de
autenticação.

- [ ] **Step 7: Atualizar entradas de deploy**

Em `terraform/terraform.tfvars.example`, substituir:

```hcl
app_base_url = "http://ENDERECO-DO-LOAD-BALANCER:8000"
```

por:

```hcl
app_listener_arn = "arn:aws:elasticloadbalancing:us-east-1:123456789012:listener/net/pytstop/LOAD_BALANCER_ID/LISTENER_ID"
```

Em `.github/workflows/cd.yml`, substituir:

```yaml
TF_VAR_app_base_url: ${{ secrets.TF_VAR_APP_BASE_URL }}
```

por:

```yaml
TF_VAR_app_listener_arn: ${{ secrets.TF_VAR_APP_LISTENER_ARN }}
```

- [ ] **Step 8: Incluir o teste Terraform no gate**

Adicionar ao `Makefile`:

```make
tf-test:
	terraform -chdir=terraform test
```

Adicionar `tf-test` ao `.PHONY` e tornar `gate` dependente de
`check tf-validate tf-test sam-validate`.

- [ ] **Step 9: Executar o gate da Lambda**

Run: `make gate`

Expected: 34 testes unitários, cobertura 100%, lint/mypy/bandit verdes,
Terraform validate/test verdes e template SAM válido.

- [ ] **Step 10: Atualizar README e MEMORY**

Documentar `app_listener_arn`, descoberta das subnets, VPC Link, parameter
mapping e novo GitHub Secret. Adicionar uma entrada no topo de `MEMORY.md`
substituindo a decisão pública anterior, sem removê-la.

- [ ] **Step 11: Commitar Lambda e Gateway**

```bash
git add terraform/variables.tf terraform/main.tf \
  terraform/terraform.tfvars.example terraform/tests/vpc_link.tftest.hcl \
  .github/workflows/cd.yml Makefile README.md MEMORY.md
git commit -m "feat: conecta Gateway ao EKS por VPC Link"
```

## Task 4: Atualizar o runbook operacional

**Files:**

- Modify: `postech-sw-arch-p3-docs/docs/runbooks/aws-academy-setup.md`
- Modify: `postech-sw-arch-p3-docs/docs/runbooks/proximas-etapas.md`
- Modify: `postech-sw-arch-p3-docs/MEMORY.md`

- [ ] **Step 1: Criar branch isolada no repositório de documentação**

Run, após confirmar que `main` está limpa:

```bash
git worktree add -b feat/aws-client-auth-integration \
  /private/tmp/postech-worktrees/postech-sw-arch-p3-docs main
```

Expected: worktree criado na mesma branch usada pelos demais repositórios.

- [ ] **Step 2: Corrigir somente os runbooks vigentes**

Em `aws-academy-setup.md`, documentar:

1. configurar credenciais default e `us-east-1`;
2. criar/validar bucket de state;
3. aplicar RDS;
4. aplicar EKS, incluindo as duas subnets privadas;
5. implantar o app e aguardar o NLB interno;
6. obter o listener ARN;
7. configurar `TF_VAR_APP_LISTENER_ARN` ou `app_listener_arn` local;
8. aplicar Lambda/Gateway/VPC Link;
9. validar o fluxo pelo endpoint público HTTPS do API Gateway;
10. desmontar na ordem inversa ao final da gravação.

Em `proximas-etapas.md`, substituir “URL do app” por “ARN do listener do NLB
interno”. Não reescrever os planos históricos de julho.

- [ ] **Step 3: Adicionar comandos somente leitura ao runbook**

Incluir:

```bash
aws elbv2 describe-load-balancers --region us-east-1 \
  --query 'LoadBalancers[?Scheme==`internal`].[LoadBalancerArn,DNSName,State.Code]'

aws elbv2 describe-listeners --region us-east-1 \
  --load-balancer-arn <NLB_ARN> \
  --query 'Listeners[?Port==`8000`].ListenerArn' --output text
```

Os comandos de `apply`, `destroy`, criação do bucket e atualização de secrets
continuam ações do usuário, salvo autorização posterior explícita.

- [ ] **Step 4: Validar documentação e registrar a decisão**

Run:

```bash
git diff --check
```

Atualizar `MEMORY.md` do repo docs apenas com o contrato operacional vigente.

- [ ] **Step 5: Commitar o runbook**

```bash
git add docs/runbooks/aws-academy-setup.md docs/runbooks/proximas-etapas.md MEMORY.md
git commit -m "docs: atualiza runbook da integração privada"
```

## Task 5: Revisão final e handoff para provisionamento

**Files:** todos os arquivos alterados nas Tasks 1–4.

- [ ] **Step 1: Rodar os gates finais em HEAD**

Run:

```bash
make gate
```

no repo EKS; depois:

```bash
make check
```

no app; e:

```bash
make gate
```

no repo Lambda.

Expected: todos os comandos com exit code `0`.

- [ ] **Step 2: Executar revisão canônica de cada diff**

Aplicar o protocolo single-shot + Judge separadamente nos repos EKS, app,
Lambda e docs. Corrigir ou rejeitar explicitamente cada finding. Reexecutar o
gate do repositório sempre que uma correção alterar o HEAD verificado.

- [ ] **Step 3: Confirmar que nenhuma mutação AWS ocorreu**

Run:

```bash
aws eks list-clusters --region us-east-1
aws rds describe-db-instances --region us-east-1 \
  --query 'DBInstances[].DBInstanceIdentifier'
aws apigatewayv2 get-apis --region us-east-1 --query 'Items[].Name'
aws elbv2 describe-load-balancers --region us-east-1 \
  --query 'LoadBalancers[].LoadBalancerName'
```

Expected antes do provisionamento: nenhum recurso do PytStop.

- [ ] **Step 4: Entregar os planos Terraform para revisão humana**

Não executar `terraform apply`. Depois que o usuário criar o bucket de state,
guiá-lo por `terraform init` e `terraform plan` na ordem RDS → EKS → app →
Lambda, validando cada resultado por AWS CLI antes do próximo passo.

> [↑ Raiz do projeto](../../../README.md)
