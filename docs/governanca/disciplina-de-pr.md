# Disciplina de PR e proteção da `main`

> [↑ Raiz do projeto](../../README.md)

> **Versão**: 1.0 — 06/10/2026. Responde ao feedback da fase 3 sobre commits diretos na `main`; decisão de CI/CD em [ADR-033](../arquitetura/adr/fase3/033-cicd-multi-repo.md) (adendos (e), (h) e (i)).

Nos cinco repositórios da fase 3 nada entra na `main` sem pull request. Este documento mostra a configuração, como qualquer pessoa confere isso sem permissão de administrador e o que o histórico contém.

## Configuração ativa

Proteção da `main` ativa desde 03/09/2026, verificada em 06/10/2026 com a conta administradora:

| Repositório | PR obrigatório | Administradores incluídos | Force-push e exclusão | Checks obrigatórios |
|---|---|---|---|---|
| `postech-sw-arch-p3` (app) | sim | sim | bloqueados | `lint`, `type-check`, `security`, `test`, `sbom`, `pip-audit`, `gitleaks`, `trivy` |
| `postech-sw-arch-p3-lambda` | sim | sim | bloqueados | `gate`, `tf-validate` |
| `postech-sw-arch-p3-infra-k8s` | sim | sim | bloqueados | `gate` |
| `postech-sw-arch-p3-infra-db` | sim | sim | bloqueados | `gate` |
| `postech-sw-arch-p3-docs` | sim | sim | bloqueados | nenhum (repositório de processo) |

O merge é sempre **squash**: cada PR vira um único commit na `main`, com o número do PR no título (`feat: ... (#32)`). No repositório principal as configurações desabilitam merge commit e rebase; nos demais a regra é do time, e `git log --merges` não encontra nenhum merge commit na `main` dos cinco. A plataforma não exige aprovação de revisor, só PR com checks verdes; a regra do time, fora da plataforma, é responder toda conversa de revisão antes do merge. O enunciado pede PR obrigatório, não revisão de terceiros.

O repositório principal tem um [template de PR](../../.github/pull_request_template.md) com a lista de verificação, e um [workflow semanal](../../.github/workflows/pr-discipline.yml) que roda a auditoria abaixo nos cinco repositórios e falha se aparecer commit direto.

## Como conferir sem ser administrador

A API de proteção (`/branches/main/protection`) exige permissão de administrador e responde 404 para leitores, mesmo com a proteção ativa. O resumo público não exige:

```bash
for r in postech-sw-arch-p3 postech-sw-arch-p3-lambda postech-sw-arch-p3-infra-k8s \
         postech-sw-arch-p3-infra-db postech-sw-arch-p3-docs; do
  gh api repos/fiap-postech-sw-architecture/$r/branches/main \
    --jq '"'$r' protected=\(.protected) checks=\(.protection.required_status_checks.contexts // [])"'
done
```

Para provar pelo histórico que não há commit direto, sem nenhuma permissão especial:

```bash
python scripts/audit_pr_discipline.py                     # os cinco repositórios
python scripts/audit_pr_discipline.py --since 2026-09-03  # exit 1 se houver violação
```

## O que o histórico contém

Resultado da auditoria em 06/10/2026 (`main` de cada repositório):

| Repositório | Commits sem PR | Último sem PR | Sem PR desde 03/09/2026 |
|---|---|---|---|
| `postech-sw-arch-p3` | 20 | 12/07/2026 | **0** |
| `postech-sw-arch-p3-lambda` | 8 | 12/07/2026 | **0** |
| `postech-sw-arch-p3-infra-k8s` | 3 | 11/07/2026 | **0** |
| `postech-sw-arch-p3-infra-db` | 3 | 11/07/2026 | **0** |
| `postech-sw-arch-p3-docs` | 17 | 11/07/2026 | **0** |

Os commits sem PR são do bootstrap da fase 3, em 11 e 12/07/2026, quando os repositórios ainda não tinham proteção; o único anterior é o commit inicial (`Initial commit`, 11/03/2026) do repositório principal. Desde a ativação da proteção, todas as mudanças entraram por PR, com os checks obrigatórios verdes.

### Por que o número do feedback é maior

Quem conta "commit direto" pelo título do `git log` (qualquer commit sem `(#N)` no fim) chega a números maiores que a auditoria por PR associado: 33 no app e 11 na Lambda. A diferença são merges feitos por PR cujo título foi customizado; o GitHub só acrescenta o `(#N)` sozinho no título padrão. Desde 06/10/2026 todo squash merge mantém o `(#N)`, e o histórico anterior permanece como está.

### Por que a história não foi reescrita

Reescrever a `main` (force-push) apagaria os commits que as evidências da entrega citam (runs do Actions, PRs e SHAs) e contraria a própria política. O registro correto é manter o histórico, documentar a data de corte e provar com a auditoria que ela vale desde então.

> [↑ Raiz do projeto](../../README.md)
