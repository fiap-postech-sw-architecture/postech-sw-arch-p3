"""Garante que os links relativos do indice da fase 3 e dos docs de governanca resolvem.

O indice existe para a banca navegar sem se perder; um link quebrado ou uma ancora
renomeada tira esse valor sem nenhum teste vermelho. Aqui cada link relativo precisa
apontar para um arquivo (ou pasta) existente e, quando houver ancora, para um titulo
real do arquivo de destino.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_RAIZ = Path(__file__).resolve().parents[3]
_DOCS = [
    _RAIZ / "docs" / "fase3" / "README.md",
    _RAIZ / "docs" / "governanca" / "disciplina-de-pr.md",
    _RAIZ / "docs" / "entrega" / "fase3" / "feedback-professor.md",
    _RAIZ / "docs" / "observabilidade" / "dashboards-grafana.md",
]
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
_TITULO = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.MULTILINE)


def _slug(titulo: str) -> str:
    """Ancora gerada pelo GitHub: minusculas, sem pontuacao, espacos viram hifens."""
    return re.sub(r"[^\w\- ]", "", titulo.lower()).replace(" ", "-")


def _ancoras(arquivo: Path) -> set[str]:
    texto = arquivo.read_text(encoding="utf-8")
    return {_slug(t) for t in _TITULO.findall(texto)}


def _links_relativos(doc: Path) -> list[tuple[str, str]]:
    achados = []
    for alvo in _LINK.findall(doc.read_text(encoding="utf-8")):
        if alvo.startswith(("http://", "https://", "mailto:", "#")):
            continue
        caminho, _, ancora = alvo.partition("#")
        achados.append((caminho, ancora))
    return achados


@pytest.mark.parametrize("doc", _DOCS, ids=lambda d: d.name)
def test_links_relativos_apontam_para_arquivos_existentes(doc: Path) -> None:
    quebrados = [
        caminho
        for caminho, _ in _links_relativos(doc)
        if not (doc.parent / caminho).resolve().exists()
    ]
    assert quebrados == []


@pytest.mark.parametrize("doc", _DOCS, ids=lambda d: d.name)
def test_ancoras_apontam_para_titulos_existentes(doc: Path) -> None:
    quebradas = []
    for caminho, ancora in _links_relativos(doc):
        destino = (doc.parent / caminho).resolve()
        if ancora and destino.suffix == ".md" and ancora not in _ancoras(destino):
            quebradas.append(f"{caminho}#{ancora}")
    assert quebradas == []


def test_slug_reproduz_as_ancoras_do_github() -> None:
    assert _slug("4. Diagrama de componentes") == "4-diagrama-de-componentes"
    assert _slug("6. Fluxo de deploy multi-repo (CI/CD)") == (
        "6-fluxo-de-deploy-multi-repo-cicd"
    )
    assert _slug("Modelo de dados (ER atualizado)") == "modelo-de-dados-er-atualizado"
