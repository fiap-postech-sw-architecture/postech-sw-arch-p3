"""Testes dos dashboards do Grafana versionados como JSON (RF-027, RNF-028).

Garantem que o ConfigMap de ``k8s/grafana.yaml`` e gerado dos JSON, que cada
painel carrega descricao e consulta, e que cada painel esta documentado em
``docs/observabilidade/dashboards-grafana.md``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts import grafana_dashboards  # noqa: E402

_DOC = _PROJECT_ROOT / "docs" / "observabilidade" / "dashboards-grafana.md"
_ARQUIVOS = grafana_dashboards.listar_dashboards()


def _carregar(arquivo: Path) -> dict[str, Any]:
    dashboard: dict[str, Any] = json.loads(arquivo.read_text(encoding="utf-8"))
    return dashboard


def test_existem_os_dois_dashboards_de_negocio_e_plataforma() -> None:
    assert [a.name for a in _ARQUIVOS] == [
        "pytstop-negocio.json",
        "pytstop-plataforma.json",
    ]


def test_configmap_esta_em_sincronia_com_os_json() -> None:
    """Falha se alguem editar o YAML (ou o JSON) sem rodar `make grafana-sync`."""
    atual = grafana_dashboards.MANIFESTO.read_text(encoding="utf-8")
    assert atual == grafana_dashboards.renderizar(atual, _ARQUIVOS)


def test_renderizar_exige_um_unico_configmap() -> None:
    with pytest.raises(ValueError, match="esperava 1 ConfigMap"):
        grafana_dashboards.renderizar("kind: ConfigMap\n", _ARQUIVOS)


def test_check_sai_com_erro_quando_fora_de_sincronia(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    copia = tmp_path / "grafana.yaml"
    copia.write_text(
        grafana_dashboards.MANIFESTO.read_text(encoding="utf-8").replace(
            '"refresh": "30s"', '"refresh": "5s"', 1
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(grafana_dashboards, "MANIFESTO", copia)
    assert grafana_dashboards.main(["--check"]) == 1
    assert grafana_dashboards.main([]) == 0  # regrava
    assert grafana_dashboards.main(["--check"]) == 0


@pytest.mark.parametrize("arquivo", _ARQUIVOS, ids=lambda a: a.stem)
def test_dashboard_tem_identidade_e_descricao(arquivo: Path) -> None:
    dashboard = _carregar(arquivo)
    assert dashboard["uid"] == arquivo.stem
    assert dashboard["title"].startswith("PytStop")
    assert dashboard["description"].strip()


@pytest.mark.parametrize("arquivo", _ARQUIVOS, ids=lambda a: a.stem)
def test_todo_painel_tem_descricao_consulta_e_posicao_valida(arquivo: Path) -> None:
    paineis = _carregar(arquivo)["panels"]
    ids = [p["id"] for p in paineis]
    assert len(ids) == len(set(ids)), "ids de painel duplicados"
    for painel in paineis:
        titulo = painel["title"]
        assert painel["description"].strip(), f"painel sem descricao: {titulo}"
        assert painel["datasource"]["uid"] == "prometheus", titulo
        assert painel["targets"], f"painel sem consulta: {titulo}"
        assert all(t["expr"].strip() for t in painel["targets"]), titulo
        pos = painel["gridPos"]
        assert pos["x"] + pos["w"] <= 24, f"painel fora da grade: {titulo}"


@pytest.mark.parametrize("arquivo", _ARQUIVOS, ids=lambda a: a.stem)
def test_todo_painel_esta_documentado(arquivo: Path) -> None:
    doc = _DOC.read_text(encoding="utf-8")
    dashboard = _carregar(arquivo)
    assert f"`{dashboard['uid']}`" in doc
    for painel in dashboard["panels"]:
        assert painel["title"] in doc, f"painel nao documentado: {painel['title']}"
