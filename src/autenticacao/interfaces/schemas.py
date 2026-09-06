from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.autenticacao.dominio.papel import Papel


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    senha: str = Field(min_length=12, max_length=128)


class RegistrarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    senha: str = Field(min_length=12, max_length=128)
    # `papel` e obrigatorio (issue #84): o endpoint e admin-gated, entao quem
    # registra escolhe explicitamente o papel. Omitir -> 422 (nunca um ADMIN
    # silencioso). Pydantic valida contra o enum Papel (StrEnum) — os valores
    # aceitos no JSON sao os papeis internos em minusculo.
    papel: Literal[Papel.ADMIN, Papel.MECANICO, Papel.ATENDENTE]

    @field_validator("papel", mode="before")
    @classmethod
    def exigir_papel_interno(cls, papel: object) -> object:
        if papel == Papel.CLIENTE:
            raise ValueError("Clientes autenticam exclusivamente por CPF")
        return papel


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    # Sem default: o valor vem do TokenDTO da aplicacao (fonte unica do
    # "bearer"); um default aqui duplicaria e mascararia divergencias.
    token_type: str


class UsuarioResponse(BaseModel):
    id: UUID
    email: str
    papel: str
