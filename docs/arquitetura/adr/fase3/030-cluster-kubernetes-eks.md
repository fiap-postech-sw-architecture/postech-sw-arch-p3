# Amazon EKS como cluster Kubernetes da fase 3

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)

* Status: Aceita
* Data: 2026-07-11

## Contexto e Problema

O Tech Challenge da fase 3 exige **cluster Kubernetes com escalabilidade** na nuvem, provisionado via **Terraform**, em **repositório próprio de infraestrutura** — ver [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md) e os requisitos RNF-025/RNF-026 no [gap analysis](../../../requisitos/fase3/gap-analysis-fase-3.md). Diferente da fase 2, em que o enunciado aceitava cluster "local ou cloud" e o [ADR-016](../fase2/016-plataforma-kubernetes.md) escolheu o kind por custo zero, a fase 3 não deixa alternativa: o cluster tem de estar na nuvem, e a nuvem da fase 3 é a AWS ([ADR-026](026-cloud-alvo-aws-academy.md)), via AWS Academy.

O ambiente AWS Academy impõe restrições que moldam a decisão (gap analysis, §5):

1. **IAM travado** — o Terraform não pode criar roles; toda role de cluster/node é a `LabRole` pré-existente ([ADR-026](026-cloud-alvo-aws-academy.md));
2. **Sessões de ~4h e budget pequeno** — infraestrutura ligada consome o crédito rápido; nada pode assumir ambiente sempre-no-ar;
3. **Credenciais rotativas** — cada sessão do lab emite credenciais novas, o que afeta o CD ([ADR-033](033-cicd-multi-repo.md)).

O snapshot herdado do p2 traz três provisionamentos que não servem mais: kind via Terraform no monorepo, AKS e VM Azure ([ADR-025](../fase2/025-ambiente-cloud-demonstracao.md)) — todos removidos do p3 (gap analysis, §4). Os manifests da aplicação em `k8s/` (Deployment, Service, HPA, ConfigMap/Secret, overlays) permanecem no repositório principal.

**Qual cluster Kubernetes hospeda o deploy cloud da fase 3, e como ele convive com o desenvolvimento local?**

## Decisão

Adotar o **Amazon EKS**, provisionado por **Terraform no repositório `postech-sw-arch-p3-infra-k8s`**, como cluster Kubernetes da fase 3 — com o **kind mantido como alvo local** de desenvolvimento e demo sem custo.

- **Provisionamento**: módulo Terraform no repo `postech-sw-arch-p3-infra-k8s` (repositório 2 dos 4 exigidos pelo challenge), com pipeline próprio ([ADR-033](033-cicd-multi-repo.md)). O material da fase 2 já ensinava exatamente este caminho — o provisionamento completo do EKS via Terraform (Terraform, Aula 08) — e o [ADR-016](../fase2/016-plataforma-kubernetes.md) previu a migração como "trocar o módulo, não o desenho".
- **Dimensionamento mínimo**: node group **gerenciado** com **2× `t3.medium`** — o menor tamanho que roda o stack (app + Redis + relay + observabilidade) com folga para o HPA escalar. Sem node group adicional, sem Fargate profile.
- **IAM**: cluster role e node role apontam para a **`LabRole`** existente do AWS Academy — o Terraform referencia a role por data source, nunca a cria (restrição documentada no [ADR-026](026-cloud-alvo-aws-academy.md)).
- **kind continua o alvo local**: o dev-loop, a demo sem custo e a validação dos manifests seguem no kind (herança da fase 2), agora provisionado pelo dev-loop do repo principal em vez do Terraform do monorepo (gap analysis, §4).
- **Manifests no repo principal**: o `k8s/` da aplicação permanece no `postech-sw-arch-p3`, ganhando um **overlay kustomize novo para EKS** (storage class, Service/exposição, ENVIRONMENT); os overlays Azure (`vm-k3s`/`cloud`) são removidos. O repo infra provisiona o **cluster**; o deploy da **aplicação** continua responsabilidade do pipeline do app.

## Alternativas Consideradas

* Amazon EKS (node group gerenciado mínimo)
* Amazon ECS Fargate
* k3s em EC2
* Azure AKS (continuidade da fase 2)

### Amazon EKS (node group gerenciado mínimo)

* Bom, porque é literalmente o que o challenge pede: "Cluster Kubernetes com escalabilidade" + "Terraform para provisionamento" — Kubernetes gerenciado de verdade, com HPA e node group elástico
* Bom, porque é a plataforma cloud de referência do material do curso — o provisionamento EKS via Terraform foi o exemplo completo da disciplina de Terraform da fase 2 (Aula 08)
* Bom, porque os manifests, probes, HPA e overlays da fase 2 são portáveis sem reescrita — o kind e o EKS são distribuições conformantes, exatamente a portabilidade que o ADR-016 preservou
* Ruim, porque o control plane do EKS é pago por hora e o node group soma custo — mitigado pelo `terraform destroy` pós-demo (runbook) e pela paridade local completa no kind
* Ruim, porque o AWS Academy limita IAM à `LabRole` — aceito como restrição de contorno ([ADR-026](026-cloud-alvo-aws-academy.md)), não impeditivo

### Amazon ECS Fargate

* Bom, porque o material da fase 3 dedica hands-on a ele — deploy de aplicação existente em ECS Fargate (Serverless, Aula 03) e exposição via ALB + API Gateway (Serverless, Aula 04)
* Bom, porque elimina a gestão de nodes (serverless de containers)
* Ruim, porque **não é Kubernetes** — o challenge exige explicitamente "Cluster Kubernetes com escalabilidade" e um repositório de "Infraestrutura Kubernetes (Terraform)"; ECS falharia o requisito central, por mais que o material o ensine
* Ruim, porque descartaria os manifests, o HPA e os overlays validados na fase 2

### k3s em EC2

* Bom, porque é barato (uma VM pequena) e é Kubernetes real — o trilho que salvou a demo da fase 2 quando o AKS foi bloqueado (ADR-025, adendo)
* Ruim, porque não é cluster **gerenciado**: control plane auto-hospedado numa VM perde exatamente o ponto que o challenge avalia (operação corporativa em Kubernetes gerenciado com escalabilidade de nós)
* Ruim, porque single-node não demonstra escalabilidade de cluster — o HPA escala pods, mas não há elasticidade de capacidade

### Azure AKS (continuidade da fase 2)

* Bom, porque o trilho `infra/azure-aks/` da fase 2 existe e o OIDC Azure já foi configurado ([ADR-025](../fase2/025-ambiente-cloud-demonstracao.md))
* Ruim, porque a nuvem da fase 3 é a AWS ([ADR-026](026-cloud-alvo-aws-academy.md)): o material da fase (Serverless, API Gateway) é todo AWS, e o AWS Academy fornece o ambiente sem custo pessoal
* Ruim, porque a subscription Azure for Students bloqueou o AKS na prática (ADR-025, adendo: policy de região + allowlist de SKU + quota zero) — não é um trilho confiável para a entrega

## Consequências

### Positivas

* O requisito central da fase 3 (cluster K8s escalável, Terraform, repo próprio) é cumprido com a plataforma de referência do curso, reusando manifests e HPA da fase 2
* Separação limpa de responsabilidades: `p3-infra-k8s` provisiona o cluster; `p3` faz o deploy da aplicação nele — espelho da segregação de repositórios exigida (RNF-025)
* O desenvolvimento diário continua com custo zero no kind; o EKS só existe quando a demo/avaliação precisa dele

### Negativas

* O **HPA existente** (`k8s/hpa.yaml`: min 1 / max 5, CPU 70% / memória 80%) **exige metrics-server no EKS** — o EKS não o instala por padrão; o provisionamento do cluster deve incluí-lo, como o kind da fase 2 já fazia (RNF-023 da fase 2)
* Budget do AWS Academy obriga disciplina operacional: `terraform destroy` após cada demo (runbook `aws-academy-setup.md` no repo `postech-sw-arch-p3-docs`); esquecer o cluster ligado consome o crédito da fase
* Dois alvos de deploy (kind local, EKS cloud) significam manter o overlay EKS testado — drift entre overlays é risco novo

### Neutras

* Versões de EKS/Kubernetes, desenho de VPC/subnets e detalhes do node group ficam no repo `postech-sw-arch-p3-infra-k8s`, fora deste ADR
* A exposição pública (LoadBalancer/Ingress) e a integração com o API Gateway (RF-026) são decididas no [ADR-027](027-api-gateway-aws.md), não aqui — o Terraform do gateway vive no repo `p3-lambda` (ADR-027), não no `p3-infra-k8s`

## Decisões Relacionadas

- [ADR-016](../fase2/016-plataforma-kubernetes.md): decidiu kind como plataforma única da fase 2 e previu a migração para EKS como troca de módulo — este ADR executa essa previsão, mantendo o kind no papel local
- [ADR-025](../fase2/025-ambiente-cloud-demonstracao.md): o trilho cloud Azure da fase 2 é encerrado; a fase 3 muda de nuvem por exigência de material e ambiente (AWS Academy)
- [ADR-026](026-cloud-alvo-aws-academy.md): fixa AWS como nuvem da fase 3 e a restrição de que o Terraform não cria IAM — a `LabRole` deste ADR vem de lá
- [ADR-031](031-banco-gerenciado-rds.md): o banco gerenciado (RDS) vive fora do cluster, em repo irmão — o Postgres deixa de ser StatefulSet in-cluster no alvo cloud
- [ADR-033](033-cicd-multi-repo.md): o pipeline do repo `p3-infra-k8s` e a ordem de deploy entre repos

## Notas

* Fonte das evidências de material: fichamentos da fase 3 (Serverless, Aulas 01–05) em `postech-sw-arch-p3-docs/docs/superpowers/research/` e da fase 2 (Terraform, Aula 08) em `local/postech-bootstrap/docs/superpowers/research/terraform.md`; as citações "(Disciplina, Aula NN)" referem-se ao material oficial da FIAP Pos Tech
* Requisitos formais: RNF-025 e RNF-026 ([gap-analysis-fase-3.md](../../../requisitos/fase3/gap-analysis-fase-3.md)); exigência original em [desafio-tech-fase-3.md](../../../requisitos/fase3/desafio-tech-fase-3.md)
* Restrições do AWS Academy (LabRole, sessões, budget) e o runbook operacional: `aws-academy-setup.md` no repo `postech-sw-arch-p3-docs`

> [↑ Raiz do projeto](../../../../README.md) · [↑ Arquitetura](../../README.md)
