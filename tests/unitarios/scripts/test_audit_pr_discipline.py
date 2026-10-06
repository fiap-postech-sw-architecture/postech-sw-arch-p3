"""Testes da auditoria de disciplina de PR (``scripts/audit_pr_discipline.py``)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts import audit_pr_discipline as audit  # noqa: E402

_PROTECAO = date(2026, 9, 3)


def _commit(dia: str, titulo: str, prs: int) -> dict[str, object]:
    return {
        "oid": "a" * 40,
        "committedDate": f"{dia}T12:00:00Z",
        "messageHeadline": titulo,
        "associatedPullRequests": {"totalCount": prs},
    }


COMMITS = [
    _commit("2026-07-11", "feat: bootstrap direto", 0),
    _commit("2026-07-12", "docs: ajuste direto", 0),
    _commit("2026-09-05", "fix: pelo PR com numero (#4)", 1),
    _commit("2026-09-10", "feat(gateway): pelo PR com titulo customizado", 1),
]


def test_classifica_commits_com_e_sem_pr() -> None:
    resumo = audit.classificar("repo", COMMITS, _PROTECAO)
    assert resumo.total == 4
    assert resumo.via_pr == 2
    assert resumo.sem_pr == 2
    assert resumo.ultimo_sem_pr == date(2026, 7, 12)


def test_titulo_sem_numero_inclui_merge_de_pr_com_titulo_customizado() -> None:
    resumo = audit.classificar("repo", COMMITS, _PROTECAO)
    # 2 diretos + 1 merge de PR cujo titulo nao recebeu o "(#N)".
    assert resumo.sem_numero_no_titulo == 3


def test_so_conta_violacao_a_partir_da_data_da_protecao() -> None:
    assert audit.classificar("repo", COMMITS, _PROTECAO).sem_pr_desde == 0
    assert audit.classificar("repo", COMMITS, date(2026, 7, 12)).sem_pr_desde == 1


def test_repo_sem_commit_direto_nao_tem_data_de_ultimo() -> None:
    resumo = audit.classificar("repo", COMMITS[2:], _PROTECAO)
    assert resumo.sem_pr == 0
    assert resumo.ultimo_sem_pr is None


def test_formatar_lista_um_repo_por_linha() -> None:
    texto = audit.formatar(
        [audit.classificar("meu-repo", COMMITS, _PROTECAO)], _PROTECAO
    )
    assert "meu-repo" in texto
    assert "2026-07-12" in texto


def test_main_sai_0_sem_violacao_e_1_com_violacao(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(audit, "buscar_commits", lambda _dono, _repo: COMMITS)
    assert audit.main(["org/repo", "--since", "2026-09-03"]) == 0
    assert "Nenhum commit direto na main" in capsys.readouterr().out
    assert audit.main(["org/repo", "--since", "2026-07-01"]) == 1
    assert "2 commit(s) sem PR" in capsys.readouterr().err


def test_main_usa_os_cinco_repos_da_fase_3_por_padrao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consultados: list[str] = []

    def falso(dono: str, repo: str) -> list[dict[str, object]]:
        consultados.append(f"{dono}/{repo}")
        return COMMITS[2:]

    monkeypatch.setattr(audit, "buscar_commits", falso)
    assert audit.main([]) == 0
    assert consultados == [f"{audit.ORGANIZACAO}/{r}" for r in audit.REPOS_FASE_3]
