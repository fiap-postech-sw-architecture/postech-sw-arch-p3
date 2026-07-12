"""Instrumentacao das metricas de negocio de OS (ADR-032, RF-027).

Um unico listener ``before_flush`` na ``Session`` observa TODA criacao e
transicao de status de ``OrdemDeServico``: qualquer caso de uso (presente ou
futuro) persiste via UnitOfWork -> flush, entao este e o choke-point que
dispensa instrumentar caso de uso por caso de uso. Dominio e aplicacao ficam
livres de observabilidade (lint-arch: infra importa dominio; o inverso nunca).

- criacao: instancia de ``OrdemDeServico`` em ``session.new`` no flush que a
  insere -> ``pytstop_os_criadas_total``. Flushes seguintes nao recontam (o
  objeto sai de ``session.new``).
- transicao: no ``before_flush``, ``_status`` (atributo puro do dominio)
  diverge de ``_status_valor`` (coluna mapeada, que o ``before_update`` do
  mapping so sincroniza DURANTE o flush) exatamente no flush que persiste a
  transicao -> observa ``pytstop_os_duracao_status_segundos`` com o label
  ``status`` = valor ANTIGO (o status em que a OS permaneceu). A duracao vem
  da history de ``_atualizado_em`` (valor carregado do banco vs o novo, que a
  transicao acabou de gravar).

ponytail: a duracao usa ``atualizado_em`` como proxy de "entrou no status em"
— exata quando nada mudou na OS durante o status anterior; adicionar/remover
item no meio subestima a permanencia daquele status. Persistir uma coluna
``status_desde`` elimina a aproximacao se os dashboards exigirem precisao.

ponytail: flush seguido de rollback (raro: violacao de constraint) conta uma
transacao desfeita; irrelevante para tendencias de dashboard.
"""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history

from src.compartilhado.infraestrutura.metrics import metricas_api
from src.ordem_servico.dominio.ordem_de_servico import OrdemDeServico

if TYPE_CHECKING:
    from sqlalchemy.orm import UOWTransaction

_instrumentado = False


def instrumentar_metricas_de_ordens() -> None:
    """Registra o listener de metricas de OS (idempotente, uma vez por processo).

    Chamado pelo composition root (``criar_app``) somente quando
    ``configurar_metricas_api`` ativou as metricas — desligadas, nenhum
    listener roda em flush algum.
    """
    global _instrumentado  # noqa: PLW0603  # init-once flag, padrao do mapping
    if _instrumentado:
        return
    _instrumentado = True  # codeql[py/unused-global-variable] -- lida na guarda
    event.listen(Session, "before_flush", _observar_flush)


def _observar_flush(
    session: Session, _flush_context: UOWTransaction, _instances: object
) -> None:
    for novo in session.new:
        if isinstance(novo, OrdemDeServico):
            metricas_api.os_criada()
    for sujo in session.dirty:
        if isinstance(sujo, OrdemDeServico):
            _observar_transicao(sujo)


def _observar_transicao(ordem: OrdemDeServico) -> None:
    """Observa a permanencia no status anterior quando este flush o troca."""
    # _status_valor e injetado em runtime pelo map_imperatively (mapping.py) e
    # ainda guarda o valor CARREGADO do banco neste ponto (o sync roda no
    # before_update, depois deste listener).
    status_anterior = getattr(ordem, "_status_valor", None)
    if not isinstance(status_anterior, str) or ordem.status.value == status_anterior:
        return
    historia = get_history(ordem, "_atualizado_em")
    if not historia.deleted:
        return
    entrou_no_status = historia.deleted[0]
    saiu_do_status = ordem.atualizado_em
    # sqlite de teste perde o timezone no round-trip (DateTime(timezone=True)
    # volta naive); producao (timestamptz) e sempre aware. Normaliza para nao
    # quebrar a subtracao aware - naive.
    if entrou_no_status.tzinfo is None and saiu_do_status.tzinfo is not None:
        entrou_no_status = entrou_no_status.replace(tzinfo=UTC)
    duracao_s = (saiu_do_status - entrou_no_status).total_seconds()
    metricas_api.os_duracao_status(status_anterior, max(duracao_s, 0.0))
