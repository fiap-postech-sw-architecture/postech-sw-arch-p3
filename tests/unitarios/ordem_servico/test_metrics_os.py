"""Unitarios do listener de metricas de negocio de OS (ADR-032, RF-027).

Contrato coberto (com Session + sqlite reais — o listener e um
``before_flush`` de ORM, entao o teste exercita o flush de verdade):

- criacao: flush que INSERE uma ``OrdemDeServico`` -> ``os_criada()`` uma vez
  (itens da ordem no mesmo flush nao recontam); flushes seguintes idem;
- transicao: flush que persiste uma troca de status -> ``os_duracao_status``
  com o label do status ANTERIOR e a duracao derivada de ``atualizado_em``
  (history do valor carregado vs o novo); mutacao sem troca de status (ex.:
  adicionar item) NAO observa nada;
- ``instrumentar_metricas_de_ordens`` e idempotente (listener unico mesmo
  chamada duas vezes);
- sem history de ``atualizado_em`` (transicao sintetica sem tocar o
  timestamp) -> nao observa (defensivo, sem crash).

A fachada e espiada via monkeypatch dos metodos do singleton ``metricas_api``
— o default (no-op) garante que o listener global registrado aqui nao polui
outros testes da suite.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

# Registra `clientes` e `veiculos` no metadata para as FKs da OS resolverem.
import src.cliente_veiculo.infraestrutura.mapping  # noqa: F401
from src.compartilhado.dominio.dinheiro import Dinheiro
from src.compartilhado.infraestrutura.database import metadata
from src.compartilhado.infraestrutura.metrics import metricas_api
from src.ordem_servico.dominio.item_da_ordem import ItemDaOrdem
from src.ordem_servico.dominio.ordem_de_servico import OrdemDeServico
from src.ordem_servico.dominio.status import StatusOrdem
from src.ordem_servico.infraestrutura.mapping import iniciar_mapeamentos
from src.ordem_servico.infraestrutura.metrics import (
    instrumentar_metricas_de_ordens,
)


@pytest.fixture
def engine_sqlite() -> Generator[Engine]:
    iniciar_mapeamentos()
    instrumentar_metricas_de_ordens()
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    try:
        yield engine
    finally:
        metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def espiao(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Espiona os metodos da fachada singleton (restaurados pelo monkeypatch)."""
    registro: dict = {"criadas": 0, "duracoes": []}

    def os_criada() -> None:
        registro["criadas"] += 1

    def os_duracao_status(status: str, duracao_s: float) -> None:
        registro["duracoes"].append((status, duracao_s))

    monkeypatch.setattr(metricas_api, "os_criada", os_criada)
    monkeypatch.setattr(metricas_api, "os_duracao_status", os_duracao_status)
    return registro


def _criar_ordem_persistida(engine: Engine) -> UUID:
    """Persiste uma OS nova e devolve o id (a instancia expira no commit)."""
    with Session(engine) as sessao:
        ordem = OrdemDeServico.criar(cliente_id=uuid4(), veiculo_id=uuid4())
        ordem_id = ordem.id
        sessao.add(ordem)
        sessao.commit()
        return ordem_id


def _item() -> ItemDaOrdem:
    return ItemDaOrdem.criar(
        servico_catalogo_id=uuid4(),
        item_estoque_id=None,
        descricao="troca de oleo",
        quantidade=1,
        preco_unitario=Dinheiro(valor=Decimal("100.00")),
    )


class TestInstrumentarIdempotente:
    def test_chamar_duas_vezes_nao_duplica_o_listener(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        # A fixture ja instrumentou; a segunda chamada precisa ser no-op —
        # senao cada flush contaria a criacao em dobro.
        instrumentar_metricas_de_ordens()
        _criar_ordem_persistida(engine_sqlite)
        assert espiao["criadas"] == 1


class TestCriacao:
    def test_flush_de_insercao_conta_uma_criada(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        _criar_ordem_persistida(engine_sqlite)
        assert espiao["criadas"] == 1
        assert espiao["duracoes"] == []

    def test_itens_no_mesmo_flush_nao_recontam(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        # session.new contem a ordem E os itens (cascade): so a OS conta.
        with Session(engine_sqlite) as sessao:
            ordem = OrdemDeServico.criar(cliente_id=uuid4(), veiculo_id=uuid4())
            ordem.adicionar_item(_item())
            sessao.add(ordem)
            sessao.commit()
        assert espiao["criadas"] == 1

    def test_flush_seguinte_nao_reconta(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        with Session(engine_sqlite) as sessao:
            ordem = OrdemDeServico.criar(cliente_id=uuid4(), veiculo_id=uuid4())
            sessao.add(ordem)
            sessao.flush()
            # Segunda mutacao + flush na MESMA session: a OS ja saiu de
            # session.new -> nao reconta.
            ordem.adicionar_item(_item())
            sessao.commit()
        assert espiao["criadas"] == 1


class TestTransicao:
    def test_transicao_observa_duracao_do_status_anterior(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        ordem_id = _criar_ordem_persistida(engine_sqlite)
        with Session(engine_sqlite) as sessao:
            carregada = sessao.get(OrdemDeServico, ordem_id)
            assert carregada is not None
            # Fixa o "entrou no status em" 5 minutos atras (committed value =
            # o que o banco devolveu) para uma duracao deterministica e para
            # cobrir o caminho aware (o sqlite devolveria naive).
            set_committed_value(
                carregada,
                "_atualizado_em",
                datetime.now(UTC) - timedelta(minutes=5),
            )
            carregada.iniciar_diagnostico()
            sessao.commit()

        (observacao,) = espiao["duracoes"]
        status, duracao_s = observacao
        assert status == StatusOrdem.RECEBIDA.value
        # ~300s (agora - committed de 5 min atras); folga generosa p/ CI lento.
        assert 295.0 <= duracao_s <= 330.0

    def test_transicao_com_committed_naive_normaliza_o_timezone(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        # sqlite devolve datetimes naive (perde o tz do DateTime(timezone=True));
        # o listener normaliza para UTC em vez de quebrar a subtracao.
        ordem_id = _criar_ordem_persistida(engine_sqlite)
        with Session(engine_sqlite) as sessao:
            carregada = sessao.get(OrdemDeServico, ordem_id)
            assert carregada is not None
            set_committed_value(
                carregada,
                "_atualizado_em",
                datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5),
            )
            carregada.iniciar_diagnostico()
            sessao.commit()

        (observacao,) = espiao["duracoes"]
        assert observacao[0] == StatusOrdem.RECEBIDA.value
        assert 295.0 <= observacao[1] <= 330.0

    def test_mutacao_sem_troca_de_status_nao_observa(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        ordem_id = _criar_ordem_persistida(engine_sqlite)
        with Session(engine_sqlite) as sessao:
            carregada = sessao.get(OrdemDeServico, ordem_id)
            assert carregada is not None
            carregada.adicionar_item(_item())  # toca atualizado_em, nao o status
            sessao.commit()
        assert espiao["duracoes"] == []

    def test_transicao_sem_history_de_atualizado_em_nao_observa(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        # Sintetico: status trocado sem tocar atualizado_em (nenhuma transicao
        # real faz isso) -> sem history nao ha duracao a derivar; o listener
        # sai limpo em vez de estourar IndexError.
        ordem_id = _criar_ordem_persistida(engine_sqlite)
        with Session(engine_sqlite) as sessao:
            carregada = sessao.get(OrdemDeServico, ordem_id)
            assert carregada is not None
            object.__setattr__(carregada, "_status", StatusOrdem.EM_DIAGNOSTICO)
            # Torna o objeto dirty sem mexer em _atualizado_em.
            carregada._cliente_id = uuid4()  # type: ignore[misc]
            sessao.commit()
        assert espiao["duracoes"] == []

    def test_duas_transicoes_em_requests_distintos_observam_cada_status(
        self, engine_sqlite: Engine, espiao: dict
    ) -> None:
        ordem_id = _criar_ordem_persistida(engine_sqlite)
        with Session(engine_sqlite) as sessao:
            carregada = sessao.get(OrdemDeServico, ordem_id)
            assert carregada is not None
            carregada.iniciar_diagnostico()
            sessao.commit()
        with Session(engine_sqlite) as sessao:
            carregada = sessao.get(OrdemDeServico, ordem_id)
            assert carregada is not None
            carregada.adicionar_item(_item())
            carregada.gerar_orcamento()
            sessao.commit()

        status_observados = [status for status, _ in espiao["duracoes"]]
        assert status_observados == [
            StatusOrdem.RECEBIDA.value,
            StatusOrdem.EM_DIAGNOSTICO.value,
        ]
