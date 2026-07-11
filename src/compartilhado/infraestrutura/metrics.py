"""Metricas Prometheus da API (ADR-032; RF-027/RNF-028).

Espelha ``relay/metrics.py`` (ADR-024): um ``MeterProvider`` OTel com
``PrometheusMetricReader`` registra os instrumentos no ``REGISTRY`` default do
``prometheus_client``; a exposicao aqui e o sub-app ASGI ``make_asgi_app()``
montado em ``/metrics`` no proprio FastAPI — o Prometheus do cluster raspa a
API na mesma porta HTTP, sem servidor extra (o relay, daemon sem ASGI, precisa
do ``start_http_server``; a API nao).

Metricas (meter ``pytstop-api``):

- ``http_request_duration`` (``unit="s"`` — o exportador anexa a unidade ao
  nome: serie ``http_request_duration_seconds``) com labels ``method``,
  ``rota`` e ``status``: latencia por rota (RNF-028), observada pelo
  ``MetricasHTTPMiddleware``. ``rota`` e o TEMPLATE da rota casada (ex.:
  ``/api/v1/ordens/{ordem_id}``), nunca o path bruto — cardinalidade limitada;
  requests sem rota casada agregam em ``nao_roteada``. Buckets 5ms..5s para
  p50/p90/p99.
- ``pytstop_os_criadas_total`` (counter): OS criadas (RF-027, volume diario
  via ``increase(...[1d])``). Incrementado pelo listener de instrumentacao em
  ``src/ordem_servico/infraestrutura/metrics.py``.
- ``pytstop_os_duracao_status_segundos`` (histogram, label ``status``):
  permanencia da OS no status ANTERIOR, observada a cada transicao (RF-027,
  tempo medio por status via ``_sum``/``_count``). SEM ``unit=``: o nome e
  contrato com os dashboards e ``unit="s"`` geraria o duplo
  ``_segundos_seconds``. Mesmo listener acima.

Erros de integracao (RF-027): NAO duplicados aqui — os counters do relay
(``outbox_falha_total`` / ``outbox_dead_total`` / ``outbox_retry_total``,
ADR-024) ja medem as falhas de entrega das integracoes; os dashboards leem
direto do alvo ``pytstop-relay``.

Default OFF: sem ``API_METRICS_ENABLED`` truthy a funcao retorna antes de
qualquer import de OpenTelemetry — custo zero para compose, CI e testes
(mesmo padrao de ``OTEL_ENABLED`` e ``RELAY_METRICS_ENABLED``; os ambientes de
demo ligam via env). Imports lazy porque o extra ``otel`` fica fora do extra
``test`` de proposito: flag ligada sem o extra degrada para warning + no-op, e
a fachada ``metricas_api`` e no-op enquanto ``configurar_metricas_api`` nao
vincula os instrumentos reais — o middleware e o listener nunca quebram.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Final

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

    # So anotacao: o extra `otel` fica fora do ambiente de lint/teste, e o
    # override `opentelemetry.*` (ignore_missing_imports) mantem o mypy verde
    # sem ele (os tipos degradam para Any nesse ambiente).
    from opentelemetry.metrics import Counter, Histogram
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response

_log = structlog.get_logger(__name__)

_VALORES_VERDADEIROS = frozenset({"true", "1"})
_NOME_METER = "pytstop-api"

# Label de rota para requests que nao casaram rota nenhuma (404 de path
# desconhecido): agrega tudo num unico valor em vez de explodir a
# cardinalidade com paths arbitrarios.
_ROTA_NAO_ROTEADA: Final = "nao_roteada"

# Buckets de latencia HTTP (RNF-028): 5ms..5s cobre do hit de cache ao pior
# caso com lock pessimista, com resolucao suficiente para p50/p90/p99.
_BUCKETS_LATENCIA_HTTP: Final = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
)

# Buckets de permanencia em status (RF-027): de 1 minuto a 7 dias — uma OS
# fica horas/dias em cada status, nao milissegundos.
_BUCKETS_DURACAO_STATUS: Final = (
    60.0,
    300.0,
    900.0,
    3600.0,
    14400.0,
    43200.0,
    86400.0,
    259200.0,
    604800.0,
)


class MetricasApi:
    """Fachada dos instrumentos da API; no-op ate ``configurar_metricas_api``.

    O middleware HTTP e o listener de ordem_servico chamam os metodos em todo
    request/flush. Enquanto as metricas estao desligadas (ou o extra ``otel``
    ausente) os instrumentos ficam ``None`` e os metodos sao no-op — os
    caminhos quentes nunca quebram nem custam nada.
    """

    def __init__(self) -> None:
        self._http_duracao: Histogram | None = None
        self._os_criadas: Counter | None = None
        self._os_duracao_status: Histogram | None = None

    def _vincular(
        self,
        *,
        http_duracao: Histogram,
        os_criadas: Counter,
        os_duracao_status: Histogram,
    ) -> None:
        self._http_duracao = http_duracao
        self._os_criadas = os_criadas
        self._os_duracao_status = os_duracao_status

    def observar_http(
        self, *, metodo: str, rota: str, status: int, duracao_s: float
    ) -> None:
        if self._http_duracao is not None:
            self._http_duracao.record(
                duracao_s,
                attributes={"method": metodo, "rota": rota, "status": str(status)},
            )

    def os_criada(self) -> None:
        if self._os_criadas is not None:
            self._os_criadas.add(1)

    def os_duracao_status(self, status: str, duracao_s: float) -> None:
        if self._os_duracao_status is not None:
            self._os_duracao_status.record(duracao_s, attributes={"status": status})


# Singleton modulo-level usado pelo middleware abaixo e pelo listener de
# ``src/ordem_servico/infraestrutura/metrics.py``. No-op por padrao;
# ``configurar_metricas_api`` vincula os instrumentos reais.
metricas_api = MetricasApi()


class MetricasHTTPMiddleware(BaseHTTPMiddleware):
    """Observa a latencia de cada request no histograma da fachada (RNF-028).

    Instalado por ``configurar_metricas_api`` (so quando as metricas estao
    ligadas). O label ``rota`` usa o path TEMPLATE da rota casada (o router
    grava ``scope["route"]`` durante o roteamento, visivel aqui apos o
    ``call_next`` porque o scope e compartilhado); sem rota casada, agrega em
    ``nao_roteada``. Excecao nao tratada conta como status 500 e segue
    propagando (o ``try/finally`` garante a observacao sem engolir o erro).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        inicio = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            metricas_api.observar_http(
                metodo=request.method,
                rota=_rota_template(request),
                status=status,
                duracao_s=time.perf_counter() - inicio,
            )


def _rota_template(request: Request) -> str:
    """Path template da rota casada (``APIRoute.path_format``/``Mount.path``)."""
    rota = request.scope.get("route")
    template = getattr(rota, "path_format", None) or getattr(rota, "path", None)
    return template if isinstance(template, str) else _ROTA_NAO_ROTEADA


def _habilitado() -> bool:
    return (
        os.environ.get("API_METRICS_ENABLED", "false").strip().lower()
        in _VALORES_VERDADEIROS
    )


def configurar_metricas_api(app: FastAPI) -> bool:
    """Liga as metricas OTel da API expostas via Prometheus (ADR-032).

    Le ``API_METRICS_ENABLED`` (default ``"false"``); quando ligada, monta um
    ``MeterProvider`` (service.name=pytstop-api, service.version=
    PYTSTOP_GIT_SHA curto) com um ``PrometheusMetricReader`` — o reader
    registra os instrumentos no ``REGISTRY`` default do ``prometheus_client``
    — monta o sub-app ``make_asgi_app()`` em ``/metrics`` e instala o
    ``MetricasHTTPMiddleware``. Deve rodar em ``criar_app`` (antes do boot do
    servidor): middleware nao pode ser adicionado com o app ja servindo.

    Returns:
        True quando as metricas foram ativadas; False quando a flag esta
        desligada ou o extra ``otel`` nao esta instalado (warning logado) —
        nesse caso nada e montado e a fachada segue no-op.
    """
    if not _habilitado():
        return False

    try:
        from opentelemetry.exporter.prometheus import PrometheusMetricReader
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource
        from prometheus_client import make_asgi_app
    except ImportError:
        _log.warning(
            "metricas da API ignoradas: API_METRICS_ENABLED=true mas o extra "
            "'otel' nao esta instalado; instale com `uv sync --extra otel`",
        )
        return False

    resource = Resource.create(
        {
            "service.name": _NOME_METER,
            # Mesmo SHA curto do banner de boot e dos logs (logging.py).
            "service.version": os.environ.get("PYTSTOP_GIT_SHA", "unknown")[:12],
        }
    )
    # O reader registra no REGISTRY default do prometheus_client; o
    # make_asgi_app montado abaixo serve esse mesmo registry em /metrics.
    reader = PrometheusMetricReader()
    provider = MeterProvider(metric_readers=[reader], resource=resource)
    meter = provider.get_meter(_NOME_METER)

    metricas_api._vincular(
        http_duracao=meter.create_histogram(
            "http_request_duration",
            unit="s",
            description="Duracao das requests HTTP da API por rota.",
            explicit_bucket_boundaries_advisory=list(_BUCKETS_LATENCIA_HTTP),
        ),
        os_criadas=meter.create_counter(
            "pytstop_os_criadas_total",
            description="Ordens de servico criadas.",
        ),
        os_duracao_status=meter.create_histogram(
            "pytstop_os_duracao_status_segundos",
            description=(
                "Permanencia (segundos) da OS no status anterior, "
                "observada a cada transicao."
            ),
            explicit_bucket_boundaries_advisory=list(_BUCKETS_DURACAO_STATUS),
        ),
    )

    app.mount("/metrics", make_asgi_app())
    app.add_middleware(MetricasHTTPMiddleware)
    _log.info("metricas da API ativas: /metrics montado")
    return True
