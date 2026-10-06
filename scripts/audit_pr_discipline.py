"""Audita a disciplina de PR: commits na ``main`` sem pull request associado.

A branch protection exige PR para entrar na ``main``; este script prova isso
pelo historico, sem precisar de permissao de admin (so le commits e PRs
associados pela API GraphQL do GitHub, via ``gh``).

Uso::

    python scripts/audit_pr_discipline.py                      # os 5 repos da fase 3
    python scripts/audit_pr_discipline.py --since 2026-09-03   # data da protecao
    python scripts/audit_pr_discipline.py org/repo [org/repo]  # outros repos

Sai com 1 se houver commit direto na ``main`` a partir de ``--since``.

Dois numeros por repositorio, porque ha duas formas de contar "commit direto":

* **sem PR**: o GitHub nao associa nenhum pull request ao commit (push direto);
* **sem (#N) no titulo**: o titulo nao termina com o numero do PR. Inclui os
  commits sem PR e tambem merges de PR feitos com titulo customizado, que o
  GitHub nao numera sozinho. E a contagem de quem le o ``git log`` a olho.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date

ORGANIZACAO = "fiap-postech-sw-architecture"
REPOS_FASE_3 = (
    "postech-sw-arch-p3",
    "postech-sw-arch-p3-lambda",
    "postech-sw-arch-p3-infra-k8s",
    "postech-sw-arch-p3-infra-db",
    "postech-sw-arch-p3-docs",
)
# Dia em que a protecao da main (PR obrigatorio, administradores incluidos) foi ativada.
PROTECAO_ATIVA_DESDE = date(2026, 9, 3)

_CONSULTA = """
query($dono: String!, $repo: String!, $depois: String) {
  repository(owner: $dono, name: $repo) {
    defaultBranchRef { target { ... on Commit {
      history(first: 100, after: $depois) {
        pageInfo { hasNextPage endCursor }
        nodes {
          oid committedDate messageHeadline
          associatedPullRequests(first: 1) { totalCount }
        }
      }
    } } }
  }
}
"""
_NUMERO_NO_TITULO = re.compile(r"\(#\d+\)\s*$")


@dataclass(frozen=True)
class Resumo:
    repo: str
    total: int
    via_pr: int
    sem_pr: int
    sem_numero_no_titulo: int
    ultimo_sem_pr: date | None
    sem_pr_desde: int


def buscar_commits(dono: str, repo: str) -> list[dict[str, object]]:
    """Todos os commits da branch padrao, paginados, com a contagem de PRs."""
    commits: list[dict[str, object]] = []
    depois: str | None = None
    while True:
        comando = ["gh", "api", "graphql", "-f", f"query={_CONSULTA}"]
        comando += ["-F", f"dono={dono}", "-F", f"repo={repo}"]
        if depois:
            comando += ["-F", f"depois={depois}"]
        saida = subprocess.run(  # noqa: S603 - comando fixo, sem entrada do usuario
            comando, check=True, capture_output=True, text=True
        ).stdout
        historico = json.loads(saida)["data"]["repository"]["defaultBranchRef"][
            "target"
        ]["history"]
        commits.extend(historico["nodes"])
        if not historico["pageInfo"]["hasNextPage"]:
            return commits
        depois = historico["pageInfo"]["endCursor"]


def classificar(repo: str, commits: list[dict[str, object]], desde: date) -> Resumo:
    """Conta commits com e sem PR e quantos sem PR ocorreram a partir de ``desde``."""

    def dia(commit: dict[str, object]) -> date:
        return date.fromisoformat(str(commit["committedDate"])[:10])

    def tem_pr(commit: dict[str, object]) -> bool:
        prs = commit["associatedPullRequests"]
        return isinstance(prs, dict) and int(prs["totalCount"]) > 0

    sem_pr = [c for c in commits if not tem_pr(c)]
    return Resumo(
        repo=repo,
        total=len(commits),
        via_pr=len(commits) - len(sem_pr),
        sem_pr=len(sem_pr),
        sem_numero_no_titulo=sum(
            1
            for c in commits
            if not _NUMERO_NO_TITULO.search(str(c["messageHeadline"]))
        ),
        ultimo_sem_pr=max((dia(c) for c in sem_pr), default=None),
        sem_pr_desde=sum(1 for c in sem_pr if dia(c) >= desde),
    )


def formatar(resumos: list[Resumo], desde: date) -> str:
    """Tabela em texto: uma linha por repositorio."""
    desde_txt = f"sem PR desde {desde.isoformat()}"
    cabecalho = (
        f"{'repositorio':<32} {'commits':>7} {'via PR':>7} {'sem PR':>7} "
        f"{'sem (#N)':>9} {'ultimo sem PR':>14} {desde_txt:>26}"
    )
    linhas = [cabecalho, "-" * len(cabecalho)]
    for r in resumos:
        ultimo = r.ultimo_sem_pr.isoformat() if r.ultimo_sem_pr else "-"
        linhas.append(
            f"{r.repo:<32} {r.total:>7} {r.via_pr:>7} {r.sem_pr:>7} "
            f"{r.sem_numero_no_titulo:>9} {ultimo:>14} {r.sem_pr_desde:>26}"
        )
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    parser.add_argument(
        "repos", nargs="*", help="repositorios (org/repo); padrao: fase 3"
    )
    parser.add_argument(
        "--since",
        type=date.fromisoformat,
        default=PROTECAO_ATIVA_DESDE,
        help="data (AAAA-MM-DD) a partir da qual commit sem PR e violacao",
    )
    args = parser.parse_args(argv)

    alvos = args.repos or [f"{ORGANIZACAO}/{r}" for r in REPOS_FASE_3]
    resumos = []
    for alvo in alvos:
        dono, _, repo = alvo.rpartition("/")
        resumos.append(
            classificar(repo, buscar_commits(dono or ORGANIZACAO, repo), args.since)
        )
    sys.stdout.write(formatar(resumos, args.since) + "\n")

    violacoes = sum(r.sem_pr_desde for r in resumos)
    if violacoes:
        sys.stderr.write(f"{violacoes} commit(s) sem PR desde {args.since}\n")
        return 1
    sys.stdout.write(f"\nNenhum commit direto na main desde {args.since}.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
