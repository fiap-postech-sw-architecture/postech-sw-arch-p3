# Scans de Segurança — Fechamento da Fase 3

> [↑ Raiz do projeto](../../README.md) · [↑ Segurança](README.md)

> **Versão**: 1.1 — atualiza a seção SonarQube com o fechamento dos 143 code smells (PR #6). Bateria executada em 11-12/07/2026 na árvore de trabalho da HEAD atual dos repositórios `p3` e `p3-lambda`. Princípio de evidência local primeiro: enquanto a cota do GitHub Actions da organização estiver esgotada, os scanners executáveis localmente rodam via gate espelho ([ADR-033](../arquitetura/adr/fase3/033-cicd-multi-repo.md)); trivy e gitleaks permanecem commitados nos workflows aguardando a cota. Sucede o [scan-fase-2.md](scan-fase-2.md), cuja baseline o snapshot da fase 3 herda.

## Escopo

Bateria da fase 3 sobre as camadas do pipeline de segurança ([ADR-011](../arquitetura/adr/011-pipeline-seguranca-analise-estatica.md)), agora cobrindo também a function serverless:

- SAST (bandit) sobre o app (`src/` + `ui/` + `relay/` + `scripts/`) e sobre o `src/` da Lambda (repo `p3-lambda`);
- SCA de dependências (pip-audit) sobre o ambiente resolvido do `uv.lock`;
- DAST (OWASP ZAP baseline) contra a API viva da stack compose (`make dast`);
- SAST semântico (CodeQL, suíte de qualidade local via `make codeql-quality`);
- SonarQube como scan manual de fechamento (não é gate de CI por decisão, TD-010/[ADR-011](../arquitetura/adr/011-pipeline-seguranca-analise-estatica.md));
- SBOM CycloneDX gerado e validado (`make sbom`, TD-012/ADR-012);
- SCA de imagem (trivy) e detecção de segredos (gitleaks): commitados no CI, pendentes da cota do Actions.

## Resumo

| Ferramenta | Tipo | Alvo | Resultado (2026-07-11) |
|---|---|---|---|
| bandit (`make security`, p3) | SAST | `src/` + `ui/` + `relay/` + `scripts/` | **0 high / 0 medium** — 10 low informativos revisados (o gate reprova em high) |
| bandit (`make security`, p3-lambda) | SAST | `src/` da function | **0 issues** em qualquer severidade |
| pip-audit | SCA (deps) | ambiente resolvido do `uv.lock` | **0 vulnerabilidades** conhecidas |
| OWASP ZAP (baseline) | DAST | API viva (stack compose, `make dast`) | **FAIL 0 · WARN 0 · PASS 65** em 58 URLs — [sumário persistido](../entrega/fase3/evidencias/zap-baseline-2026-07-11.txt) |
| CodeQL (suíte de qualidade) | SAST semântico | código Python (`make codeql-quality`) | **0 findings ativos** |
| SonarQube (Community, local) | Análise estática + hotspots | `src/` + coverage importado | **Quality Gate Passed** — 0 bugs, 0 vulnerabilities, 0 hotspots, 0 code smells (143 zerados no PR #6), ratings A/A/A; 94,6% no denominador do Sonar (gate real 96,8%) |
| SBOM (CycloneDX, `make sbom`) | Inventário de dependências | deps de runtime do `uv.lock` | **Gerado e validado** — 48 refs |
| trivy · gitleaks | SCA (imagem) / segredos | imagem Docker, árvore git | **Pendentes da cota do Actions** — commitados no CI; última execução verde em [scan-fase-2.md](scan-fase-2.md) |

## Análise Estática (bandit)

Gate do projeto (`make security`) reprova em high. No app: 0 high / 0 medium; os 10 low são achados informativos revisados (asserts de teste-guarda, subprocess de tooling e afins). Na Lambda (`p3-lambda`, mesmo alvo `make security`): nenhum achado em qualquer severidade.

## Auditoria de Dependências (pip-audit)

Execução efêmera (`uv run --with pip-audit pip-audit`) sobre o ambiente resolvido do lockfile: 0 vulnerabilidades conhecidas (apenas o pacote local `pytstop` não auditável, por não ser publicado no PyPI — esperado).

## DAST (OWASP ZAP baseline)

`make dast` contra a API viva da stack compose dedicada: FAIL 0 · WARN 0 · PASS 65 em 58 URLs, com as 2 regras IGNORE herdadas do baseline ([`.zap/rules.tsv`](../../.zap/rules.tsv)). Sumário persistido em [`docs/entrega/fase3/evidencias/zap-baseline-2026-07-11.txt`](../entrega/fase3/evidencias/zap-baseline-2026-07-11.txt).

## SAST Semântico (CodeQL)

Suíte de qualidade local (`make codeql-quality`, paridade com o default setup do GitHub): 0 findings ativos; os achados brutos estão todos tratados por configuração ou supressão justificada. Nesta rodada, 1 constante morta removida e 2 falsos positivos suprimidos com razão registrada.

## SonarQube (scan manual de fechamento)

SonarQube Community local + `sonar-scanner` com coverage importado: Quality Gate **Passed**, com 0 bugs, 0 vulnerabilities, 0 security hotspots, 0 code smells e 0% duplicação. Cobertura de 94,6% no denominador do Sonar (o gate real do projeto mede 96,8%; divergência de universo documentada no `sonar-project.properties`). Screenshot do Quality Gate em [entrega/fase3/evidencias/sonarqube-quality-gate-fase3.png](../entrega/fase3/evidencias/sonarqube-quality-gate-fase3.png).

O primeiro scan apontou 3 security hotspots (os mesmos da fase 2: ReDoS na regex de e-mail e dois avisos de `http://` no exporter OTLP) — todos revisados como SAFE com justificativa inline no código — e **143 code smells** de maintainability (rating A, até então informativos, nunca corrigidos). Os 143 foram zerados no [PR #6](https://github.com/fiap-postech-sw-architecture/postech-sw-arch-p3/pull/6):

| Regra | Qtd | Correção |
|---|---|---|
| S8410 | 98 | `param: Tipo = Depends(...)` → `Annotated[Tipo, Depends(...)]` nos 7 routers (exigiu `Session` em import runtime + `# noqa: TC002`: `Annotated[Session, Depends(...)]` é resolvido em runtime pelo FastAPI mesmo com `from __future__ import annotations`) |
| S8409 | 17 | `response_model` redundante removido (idêntico ao retorno anotado — OpenAPI byte-idêntico antes/depois) |
| S1186 | 22 | Docstrings de contrato nos métodos abstratos dos ports de domínio + `unit_of_work` |
| S5886 | 3 | `copy.replace` (py3.13+) devolve o tipo concreto do DTO nas queries de OS, sem cast |
| S1110 | 2 | Parênteses redundantes |
| S3776 | 1 | Complexidade cognitiva do mapeamento de veículo reduzida de 19 para 9 (funções de reidratação içadas) |

Verificação: `make check` verde (ruff + lint-arch + mypy strict + bandit), suíte completa 100% verde sem erro de coleta (o registro de rotas do FastAPI acontece em import — um `Annotated`/import quebrado estouraria a coleta, não só uma asserção). Re-scan na HEAD final confirma `code_smells: 0`.

## SBOM (CycloneDX)

`make sbom` gera e valida o `sbom.cdx.json` a partir das dependências de runtime do lockfile: 48 refs de componentes inventariados.

## Pendentes (trivy · gitleaks)

Os gates de trivy (imagem) e gitleaks (segredos) estão commitados nos workflows e aguardam a renovação da cota do GitHub Actions da organização; não há executor local equivalente configurado para esta bateria. Última execução verde registrada no [scan-fase-2.md](scan-fase-2.md), herdada pelo snapshot.

## Relação com Outros Documentos

- [Documento de entrega da fase 3, §5](../entrega/fase3/entrega-fase-3.md): relatório de vulnerabilidades da entrega
- [Scans de fechamento da fase 2](scan-fase-2.md): baseline herdada pelo snapshot
- [Relatório de vulnerabilidades (fase 1)](relatorio-vulnerabilidades.md): baseline OWASP API Top 10
- [Plano de segurança](plano-seguranca.md): modelo de ameaças e controles
- [ADR-011](../arquitetura/adr/011-pipeline-seguranca-analise-estatica.md): pipeline de segurança em camadas

> [↑ Raiz do projeto](../../README.md) · [↑ Segurança](README.md)
