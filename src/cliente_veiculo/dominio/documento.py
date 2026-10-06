from __future__ import annotations

import re
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable

# re.ASCII: sem a flag, \D e Unicode e deixa passar digitos de outros alfabetos
# (ex.: arabe-indicos), que o brutils aceita e que gerariam um documento_hash
# diferente do mesmo CPF em ASCII -- duplicando o cadastro apesar da UK.
_NAO_DIGITO = re.compile(r"\D", re.ASCII)


def normalizar_e_validar(
    numero: str, rotulo: str, validador: Callable[[str], bool]
) -> str:
    """Remove mascara e valida com o validador brutils; ValueError se invalido.

    Helper unico compartilhado por CPF e CNPJ: a normalizacao (descarte de
    tudo que nao e digito ASCII) e identica, mudando apenas o validador (`is_valid`
    de `brutils.cpf`/`brutils.cnpj`) e o rotulo da mensagem de erro.
    """
    normalizado = _NAO_DIGITO.sub("", numero)
    if not validador(normalizado):
        msg = f"{rotulo} invalido"
        raise ValueError(msg)
    return normalizado


class Documento(Protocol):
    """Contrato para documentos de identificacao fiscal (CPF, CNPJ).

    Define a interface comum exigida pelo agregado Cliente e pelos repositorios.
    Implementacoes (CPF, CNPJ) satisfazem este Protocol estruturalmente: basta
    expor `numero` (read-only), `formatado()` e `mascarado()`.
    """

    # corpos `pass` (nao `...`) evitam o FP CodeQL py/ineffectual-statement
    @property
    def numero(self) -> str:
        """Numero puro do documento (sem mascara), usado para busca por hash."""
        pass

    def formatado(self) -> str:
        """Retorna o documento formatado por extenso para exibicao ao usuario."""
        pass

    def mascarado(self) -> str:
        """Retorna o documento com os digitos centrais ocultos (seguro para logs)."""
        pass
