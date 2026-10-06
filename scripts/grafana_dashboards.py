"""Sincroniza os dashboards JSON do Grafana com o ConfigMap de ``k8s/grafana.yaml``.

Fonte unica: ``k8s/grafana/dashboards/*.json`` -- arquivos revisaveis e
importaveis direto no Grafana (Dashboards > Import). O ConfigMap
``grafana-dashboards`` de ``k8s/grafana.yaml`` e GERADO a partir deles, de modo
que ``kubectl apply -f k8s/*.yaml`` (kind e CD) e o overlay do EKS continuam
funcionando sem kustomize adicional.

Uso::

    python scripts/grafana_dashboards.py          # regrava o ConfigMap
    python scripts/grafana_dashboards.py --check  # exit 1 se estiver fora de sincronia
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DASHBOARDS_DIR = RAIZ / "k8s" / "grafana" / "dashboards"
MANIFESTO = RAIZ / "k8s" / "grafana.yaml"

_SEPARADOR = "\n---\n"
_NOME_CONFIGMAP = re.compile(r"^  name: grafana-dashboards$", re.MULTILINE)


def listar_dashboards(diretorio: Path = DASHBOARDS_DIR) -> list[Path]:
    """Arquivos JSON de dashboard em ordem alfabetica (ordem estavel no ConfigMap)."""
    return sorted(diretorio.glob("*.json"))


def _bloco_data(arquivos: list[Path]) -> str:
    """Bloco ``data:`` do ConfigMap: cada JSON como escalar literal indentado."""
    linhas = ["data:"]
    for arquivo in arquivos:
        texto = arquivo.read_text(encoding="utf-8")
        json.loads(texto)  # falha cedo, com o nome do arquivo, em JSON invalido
        linhas.append(f"  {arquivo.name}: |")
        linhas.extend(
            f"    {linha}" if linha else "" for linha in texto.rstrip("\n").split("\n")
        )
    return "\n".join(linhas) + "\n"


def renderizar(manifesto: str, arquivos: list[Path]) -> str:
    """Devolve ``manifesto`` com o bloco ``data:`` do ConfigMap regenerado."""
    documentos = manifesto.split(_SEPARADOR)
    alvos = [i for i, doc in enumerate(documentos) if _NOME_CONFIGMAP.search(doc)]
    if len(alvos) != 1:
        msg = f"esperava 1 ConfigMap grafana-dashboards, achei {len(alvos)}"
        raise ValueError(msg)
    doc = documentos[alvos[0]]
    inicio = doc.index("\ndata:\n") + 1
    documentos[alvos[0]] = doc[:inicio] + _bloco_data(arquivos).rstrip("\n") + "\n"
    return _SEPARADOR.join(documentos)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="falha se o ConfigMap estiver desatualizado",
    )
    args = parser.parse_args(argv)

    atual = MANIFESTO.read_text(encoding="utf-8")
    esperado = renderizar(atual, listar_dashboards())
    if args.check:
        if atual != esperado:
            sys.stderr.write(
                "k8s/grafana.yaml fora de sincronia com k8s/grafana/dashboards/*.json; "
                "rode: python scripts/grafana_dashboards.py\n"
            )
            return 1
        return 0
    MANIFESTO.write_text(esperado, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
