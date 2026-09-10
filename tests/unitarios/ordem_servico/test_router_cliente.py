from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.autenticacao.interfaces.middleware import obter_usuario_atual
from src.compartilhado.interfaces.dependencies import obter_session
from src.compartilhado.interfaces.error_handler import registrar_error_handlers
from src.ordem_servico.dominio.exceptions import OrdemNaoEncontradaException
from src.ordem_servico.interfaces.router_cliente import router

_AGORA = datetime.now(tz=UTC)
_ORDEM_NS = SimpleNamespace(
    id=uuid4(),
    cliente_id=uuid4(),
    veiculo_id=uuid4(),
    status="recebida",
    itens=[],
    orcamento=None,
    criado_em=_AGORA,
    atualizado_em=_AGORA,
)


def _criar_app(usuario: dict[str, object]) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    session = MagicMock()
    app.dependency_overrides[obter_session] = lambda: session
    app.dependency_overrides[obter_usuario_atual] = lambda: usuario
    return app


@pytest.fixture(autouse=True)
def _enriquecimento_identidade() -> Iterator[None]:
    stub = MagicMock()
    stub.executar.side_effect = lambda dto: dto
    stub.executar_lote.side_effect = lambda dtos: dtos
    with patch(
        "src.ordem_servico.interfaces.router_cliente.obter_enriquecer_ordem",
        return_value=stub,
    ):
        yield


def test_lista_repassa_cliente_e_paginacao() -> None:
    cliente_id = uuid4()
    app = _criar_app({"sub": str(cliente_id), "papel": "cliente"})
    with patch(
        "src.ordem_servico.interfaces.router_cliente.obter_listar_ordens_do_cliente"
    ) as factory:
        uc = factory.return_value
        uc.executar.return_value = []
        uc.contar.return_value = 0
        response = TestClient(app).get(
            "/api/v1/minhas-ordens?offset=2&limit=5&incluir_encerradas=true"
        )

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "offset": 2, "limit": 5}
    uc.executar.assert_called_once_with(
        cliente_id,
        offset=2,
        limit=5,
        incluir_encerradas=True,
    )
    uc.contar.assert_called_once_with(cliente_id, incluir_encerradas=True)


def test_detalhe_repassa_ordem_e_cliente() -> None:
    cliente_id = uuid4()
    ordem_id = uuid4()
    app = _criar_app({"sub": str(cliente_id), "papel": "cliente"})
    with patch(
        "src.ordem_servico.interfaces.router_cliente.obter_ordem_do_cliente"
    ) as factory:
        factory.return_value.executar.return_value = _ORDEM_NS
        response = TestClient(app).get(f"/api/v1/minhas-ordens/{ordem_id}")

    assert response.status_code == 200
    factory.return_value.executar.assert_called_once_with(ordem_id, cliente_id)


def test_papel_interno_retorna_403() -> None:
    app = _criar_app({"sub": str(uuid4()), "papel": "admin"})
    assert TestClient(app).get("/api/v1/minhas-ordens").status_code == 403


def test_sub_invalido_retorna_401() -> None:
    app = _criar_app({"sub": "invalido", "papel": "cliente"})
    assert TestClient(app).get("/api/v1/minhas-ordens").status_code == 401


def test_ordem_de_outro_cliente_retorna_404() -> None:
    # O use case trata ordem alheia como inexistente (anti-enumeracao, RN-021);
    # aqui se prova que esse erro de dominio vira 404 HTTP, nao 500.
    app = _criar_app({"sub": str(uuid4()), "papel": "cliente"})
    registrar_error_handlers(app)
    with patch(
        "src.ordem_servico.interfaces.router_cliente.obter_ordem_do_cliente"
    ) as factory:
        factory.return_value.executar.side_effect = OrdemNaoEncontradaException(uuid4())
        response = TestClient(app).get(f"/api/v1/minhas-ordens/{uuid4()}")

    assert response.status_code == 404
