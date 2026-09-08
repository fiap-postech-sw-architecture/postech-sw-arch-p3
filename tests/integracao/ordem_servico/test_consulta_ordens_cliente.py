"""Integracao das consultas de ordens limitadas ao cliente autenticado."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest

from src.cliente_veiculo.dominio.cliente import Cliente
from src.cliente_veiculo.dominio.contato import Contato
from src.cliente_veiculo.dominio.cpf import CPF
from src.cliente_veiculo.dominio.placa import Placa
from src.cliente_veiculo.infraestrutura.repository import (
    ClienteSQLAlchemyRepository,
)
from src.ordem_servico.dominio.status import StatusOrdem
from src.ordem_servico.infraestrutura.mapping import ordens_de_servico_table
from src.ordem_servico.infraestrutura.repository import (
    OrdemDeServicoSQLAlchemyRepository,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integracao

_AGORA = datetime(2026, 9, 6, tzinfo=UTC)


def _criar_cliente_com_veiculo(
    session: Session, cpf: str, placa: str
) -> tuple[UUID, UUID]:
    cliente = Cliente(
        _nome="Cliente da consulta",
        _documento=CPF(numero=cpf),
        _contato=Contato(valor="11999990000"),
    )
    ClienteSQLAlchemyRepository(session=session).salvar(cliente)
    cliente.adicionar_veiculo(
        placa=Placa(valor=placa), marca="Fiat", modelo="Uno", ano=2020
    )
    session.flush()
    return cliente.id, cliente.veiculos[0].id


def _inserir_ordem(
    session: Session,
    cliente_id: UUID,
    veiculo_id: UUID,
    status: StatusOrdem,
) -> UUID:
    ordem_id = uuid4()
    session.execute(
        ordens_de_servico_table.insert().values(
            id=ordem_id,
            cliente_id=cliente_id,
            veiculo_id=veiculo_id,
            status=status.value,
            orcamento_json=None,
            criado_em=_AGORA,
            atualizado_em=_AGORA,
        )
    )
    session.flush()
    return ordem_id


def test_lista_somente_ordens_do_cliente(session: Session) -> None:
    cliente_a, veiculo_a = _criar_cliente_com_veiculo(session, "21249722519", "CLI1001")
    cliente_b, veiculo_b = _criar_cliente_com_veiculo(session, "52998224725", "CLI1002")
    ordem_a = _inserir_ordem(session, cliente_a, veiculo_a, StatusOrdem.RECEBIDA)
    _inserir_ordem(session, cliente_b, veiculo_b, StatusOrdem.RECEBIDA)
    repo = OrdemDeServicoSQLAlchemyRepository(session)

    resultado = repo.listar_por_cliente(cliente_a, offset=0, limit=20)

    assert [ordem.id for ordem in resultado] == [ordem_a]
    assert repo.contar_por_cliente(cliente_a, incluir_encerradas=False) == 1


def test_filtro_de_encerradas_preserva_o_escopo_do_cliente(
    session: Session,
) -> None:
    cliente_id, veiculo_id = _criar_cliente_com_veiculo(
        session, "21249722519", "CLI3001"
    )
    outro_cliente_id, outro_veiculo_id = _criar_cliente_com_veiculo(
        session, "52998224725", "CLI3002"
    )
    _inserir_ordem(session, cliente_id, veiculo_id, StatusOrdem.RECEBIDA)
    _inserir_ordem(session, cliente_id, veiculo_id, StatusOrdem.CANCELADA)
    _inserir_ordem(
        session,
        outro_cliente_id,
        outro_veiculo_id,
        StatusOrdem.CANCELADA,
    )
    repo = OrdemDeServicoSQLAlchemyRepository(session)

    assert len(repo.listar_por_cliente(cliente_id)) == 1
    assert len(repo.listar_por_cliente(cliente_id, incluir_encerradas=True)) == 2
    assert repo.contar_por_cliente(cliente_id, incluir_encerradas=False) == 1
    assert repo.contar_por_cliente(cliente_id, incluir_encerradas=True) == 2


def test_detalhe_exige_id_e_cliente(session: Session) -> None:
    cliente_a, veiculo_a = _criar_cliente_com_veiculo(session, "21249722519", "CLI2001")
    cliente_b, _ = _criar_cliente_com_veiculo(session, "52998224725", "CLI2002")
    ordem_id = _inserir_ordem(session, cliente_a, veiculo_a, StatusOrdem.RECEBIDA)
    repo = OrdemDeServicoSQLAlchemyRepository(session)

    assert repo.obter_por_id_e_cliente(ordem_id, cliente_a) is not None
    assert repo.obter_por_id_e_cliente(ordem_id, cliente_b) is None
