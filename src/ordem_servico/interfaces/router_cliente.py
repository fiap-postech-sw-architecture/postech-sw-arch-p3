"""Consultas de ordens limitadas ao cliente autenticado."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID  # noqa: TC003

from fastapi import APIRouter, Depends, Query

# Runtime import: o FastAPI avalia a annotation da dependencia em runtime.
from sqlalchemy.orm import Session  # noqa: TC002

from src.autenticacao.interfaces.middleware import obter_cliente_id_atual
from src.compartilhado.interfaces.dependencies import obter_session
from src.ordem_servico.interfaces.dependencies import (
    obter_enriquecer_ordem,
    obter_listar_ordens_do_cliente,
    obter_ordem_do_cliente,
)
from src.ordem_servico.interfaces.schemas import (
    OrdemDeServicoResponse,
    OrdemListaResponse,
    OrdemResumoResponse,
)

router = APIRouter(prefix="/api/v1/minhas-ordens", tags=["minhas-ordens"])


@router.get("", summary="Lista as ordens do cliente autenticado")
def listar_minhas_ordens(
    *,
    cliente_id: Annotated[UUID, Depends(obter_cliente_id_atual)],
    session: Annotated[Session, Depends(obter_session)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    incluir_encerradas: bool = False,
) -> OrdemListaResponse:
    uc = obter_listar_ordens_do_cliente(session)
    items = uc.executar(
        cliente_id,
        offset=offset,
        limit=limit,
        incluir_encerradas=incluir_encerradas,
    )
    total = uc.contar(cliente_id, incluir_encerradas=incluir_encerradas)
    enriquecidos = obter_enriquecer_ordem(session).executar_lote(items)
    return OrdemListaResponse(
        items=[OrdemResumoResponse.model_validate(item) for item in enriquecidos],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{ordem_id}", summary="Consulta uma ordem do cliente autenticado")
def obter_minha_ordem(
    ordem_id: UUID,
    cliente_id: Annotated[UUID, Depends(obter_cliente_id_atual)],
    session: Annotated[Session, Depends(obter_session)],
) -> OrdemDeServicoResponse:
    dto = obter_ordem_do_cliente(session).executar(ordem_id, cliente_id)
    enriquecido = obter_enriquecer_ordem(session).executar(dto)
    return OrdemDeServicoResponse.model_validate(enriquecido)
