"""Entrypoint pytest: executa os planos full e ci contra instancia viva.

Dois testes principais:
  - ``test_plano_full`` — marker ``slowest``, executa ``plano_full``
  - ``test_plano_ci`` — marker ``slow``, executa ``plano_ci``

Cada teste escreve o ``ResultadoAgregado`` em ``full-test/reports/<timestamp>.json``
antes de avaliar sucesso, para que o JSON seja sempre consumido mesmo em falha.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from full_test.orchestrator.executar import ParallelOrchestrator
from full_test.orchestrator.planos import plano_ci, plano_full

if TYPE_CHECKING:
    from full_test.orchestrator.executar import ResultadoAgregado
    from full_test.seeders.config import FullTestConfig


_REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _registrar_relatorio(agregado: ResultadoAgregado, sufixo: str) -> Path:
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destino = _REPORTS_DIR / f"{timestamp}-{sufixo}.json"
    destino.write_text(json.dumps(agregado.para_dict(), indent=2), encoding="utf-8")
    return destino


def _falhar_com_resumo(agregado: ResultadoAgregado) -> None:
    """Monta mensagem humana e levanta AssertionError se algum journey nao-OK existe."""
    if agregado.sucesso():
        return

    falhas = [r for r in agregado.resultados if r.status.value != "ok"]
    linhas = [
        f"- {r.journey_name}#{r.instance_id} [{r.status.value}]: {r.falha}"
        for r in falhas[:20]
    ]
    restante = len(falhas) - 20
    if restante > 0:
        linhas.append(f"  ... e mais {restante} falhas")

    raise AssertionError(
        f"Plano '{agregado.plano}' teve {agregado.resumo.falhou} falhas "
        f"+ {agregado.resumo.timeout} timeouts de {agregado.resumo.total}:\n"
        + "\n".join(linhas)
    )


# Mesmo racional do timeout de test_plano_ci: o backoff de rate-limit do /login
# (5/min) e legitimo e pode passar de duas janelas de Retry-After (~65s cada);
# o teto global de 120s do pyproject cortaria antes. Replica o fix do PR #200
# do p2 (que fixou os dois testes; aqui o test_plano_ci ja tinha, faltava este).
@pytest.mark.timeout(300)
@pytest.mark.slowest
def test_plano_full(config: FullTestConfig, seed_recursos: dict[str, Any]) -> None:
    """Roda o plano completo incluindo sleeps reais (E2E integrado completo).

    Passou a rodar em CI (full-test-ci.yml, marker ``slowest``), validando o
    fluxo completo a cada PR/push/nightly. E superset de ``test_plano_ci``, que
    fica para execucao local rapida.
    """
    orquestrador = ParallelOrchestrator(config=config)
    plano = plano_full(
        n_clientes=config.n_clientes,
        n_operadores=config.n_operadores,
        n_admins=config.n_admins,
    )
    agregado = orquestrador.executar(plano, recursos_seed=seed_recursos)
    destino = _registrar_relatorio(agregado, "full")
    print(f"Relatorio: {destino}")
    _falhar_com_resumo(agregado)


# timeout proprio (pyproject deixa o teto global em 120s): o plano contem a
# RbacMatrixJourney com timeout_s=180 (+5 de folga) e, em maquina rapida, ate
# duas esperas de janela do rate limit de /login (~65s cada) — 120s mata o
# teste antes de o proprio orquestrador decidir (observado local 2026-07-11).
@pytest.mark.timeout(300)
@pytest.mark.slow
def test_plano_ci(config: FullTestConfig, seed_recursos: dict[str, Any]) -> None:
    """Roda o plano reduzido sem sleeps — roda em CI."""
    orquestrador = ParallelOrchestrator(config=config)
    plano = plano_ci(
        n_clientes=config.n_clientes,
        n_operadores=config.n_operadores,
        n_admins=config.n_admins,
    )
    agregado = orquestrador.executar(plano, recursos_seed=seed_recursos)
    destino = _registrar_relatorio(agregado, "ci")
    print(f"Relatorio: {destino}")
    _falhar_com_resumo(agregado)
