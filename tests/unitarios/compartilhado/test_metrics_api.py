"""Unitarios de ``configurar_metricas_api`` + middleware (ADR-032, RF-027/RNF-028).

Contrato coberto:

- flag ``API_METRICS_ENABLED`` desligada (ausente ou false) -> ``False`` sem
  efeito algum: nenhum import de OpenTelemetry, nenhum mount/middleware, a
  fachada ``metricas_api`` continua no-op;
- flag ligada sem o extra ``otel`` instalado -> ``False`` + warning acionavel
  (boot da API nunca quebra por dependencia ausente);
- flag ligada com dependencias presentes (stubs em ``sys.modules``) ->
  ``True`` com MeterProvider montado, os instrumentos criados com os NOMES
  EXATOS do contrato dos dashboards, a fachada vinculada, ``/metrics``
  montado e o ``MetricasHTTPMiddleware`` instalado;
- middleware HTTP: observa {method, rota-template, status, duracao}; 404 sem
  rota casada agrega em ``nao_roteada``; excecao conta como 500 e propaga.

Os stubs simulam os modulos otel/prometheus em ``sys.modules`` para que a
suite rode identica com ou sem o extra ``otel`` instalado (o CI nao instala o
extra). Espelha ``tests/unitarios/relay/test_metrics.py``.
"""

from __future__ import annotations

import sys
import types

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

import src.compartilhado.infraestrutura.metrics as metrics_modulo
from src.compartilhado.infraestrutura.metrics import (
    MetricasApi,
    MetricasHTTPMiddleware,
    configurar_metricas_api,
    metricas_api,
)


@pytest.fixture(autouse=True)
def _logger_fresco(monkeypatch: pytest.MonkeyPatch) -> None:
    # capture_logs nao intercepta loggers ja "bound"/cacheados
    # (configurar_logging usa cache_logger_on_first_use=True). Um proxy novo por
    # teste devolve o capture deterministico em qualquer ordem da suite.
    monkeypatch.setattr(
        metrics_modulo, "_log", structlog.get_logger("test_metrics_api")
    )


@pytest.fixture(autouse=True)
def facade_isolada(monkeypatch: pytest.MonkeyPatch) -> MetricasApi:
    # configurar_metricas_api vincula o singleton de modulo `metricas_api`;
    # troca por uma instancia fresca por teste para nao vazar instrumentos.
    fachada = MetricasApi()
    monkeypatch.setattr(metrics_modulo, "metricas_api", fachada)
    return fachada


def _bloquear_imports_otel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forca ImportError em ``import opentelemetry...`` / ``import prometheus_client``.

    Remove os modulos ja importados (caso o extra esteja instalado e outro teste
    os tenha carregado) e poe ``None`` na raiz — o import system trata ``None``
    em ``sys.modules`` como import proibido e levanta ImportError.
    """
    for nome in [
        m
        for m in sys.modules
        if m == "opentelemetry"
        or m.startswith("opentelemetry.")
        or m == "prometheus_client"
        or m.startswith("prometheus_client.")
    ]:
        monkeypatch.delitem(sys.modules, nome)
    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    monkeypatch.setitem(sys.modules, "prometheus_client", None)


class CounterStub:
    def __init__(self, nome: str) -> None:
        self.nome = nome
        self.total = 0

    def add(self, amount: int) -> None:
        self.total += amount


class HistogramStub:
    def __init__(self, nome: str) -> None:
        self.nome = nome
        self.registros: list[tuple[float, dict | None]] = []

    def record(self, amount: float, attributes: dict | None = None) -> None:
        self.registros.append((amount, attributes))


@pytest.fixture
def otel_stubs(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Instala stubs dos modulos otel/prometheus e devolve o registro de chamadas."""
    registro: dict = {
        "counters": {},
        "histogramas": {},
        "kwargs": {},
    }

    class ResourceStub:
        @classmethod
        def create(cls, attributes: dict) -> ResourceStub:
            registro["resource_attributes"] = attributes
            return cls()

    class MeterStub:
        def create_counter(self, nome: str, **kwargs: object) -> CounterStub:
            contador = CounterStub(nome)
            registro["counters"][nome] = contador
            registro["kwargs"][nome] = kwargs
            return contador

        def create_histogram(self, nome: str, **kwargs: object) -> HistogramStub:
            histograma = HistogramStub(nome)
            registro["histogramas"][nome] = histograma
            registro["kwargs"][nome] = kwargs
            return histograma

    class MeterProviderStub:
        def __init__(self, *, metric_readers: list, resource: object) -> None:
            registro["provider"] = self
            registro["metric_readers"] = metric_readers
            registro["provider_resource"] = resource

        def get_meter(self, nome: str) -> MeterStub:
            registro["meter_nome"] = nome
            return MeterStub()

    class PrometheusMetricReaderStub:
        def __init__(self) -> None:
            registro["reader"] = self

    async def asgi_app_stub(scope: dict, receive: object, send: object) -> None:
        raise NotImplementedError  # nunca chamado nos testes

    def make_asgi_app_stub() -> object:
        registro["asgi_app"] = asgi_app_stub
        return asgi_app_stub

    simbolos_por_modulo = {
        "opentelemetry.exporter.prometheus": {
            "PrometheusMetricReader": PrometheusMetricReaderStub
        },
        "opentelemetry.sdk.metrics": {"MeterProvider": MeterProviderStub},
        "opentelemetry.sdk.resources": {"Resource": ResourceStub},
        "prometheus_client": {"make_asgi_app": make_asgi_app_stub},
    }

    # Registra cada modulo-alvo e todos os pacotes intermediarios: o import
    # system resolve pais antes dos filhos em `from a.b.c import d`.
    instalados: dict[str, types.ModuleType] = {}
    for caminho, simbolos in simbolos_por_modulo.items():
        partes = caminho.split(".")
        for i in range(1, len(partes) + 1):
            prefixo = ".".join(partes[:i])
            if prefixo not in instalados:
                instalados[prefixo] = types.ModuleType(prefixo)
        for nome, valor in simbolos.items():
            setattr(instalados[caminho], nome, valor)
    for caminho, modulo in instalados.items():
        monkeypatch.setitem(sys.modules, caminho, modulo)

    return registro


# ---------------------------------------------------------------------------
# Fachada no-op (independe do extra; e o caminho quente de request/flush)
# ---------------------------------------------------------------------------


class TestFachadaNoOp:
    def test_chamadas_sem_vinculo_nao_quebram(self) -> None:
        # Sem configurar_metricas_api os instrumentos ficam None: as chamadas
        # do middleware e do listener precisam ser no-op silenciosos.
        fachada = MetricasApi()
        fachada.observar_http(metodo="GET", rota="/x", status=200, duracao_s=0.1)
        fachada.os_criada()
        fachada.os_duracao_status("recebida", 60.0)
        # Nada a asseverar alem de nao levantar: o contrato e "nunca quebra".

    def test_singleton_de_modulo_e_no_op_por_padrao(self) -> None:
        metricas_api.observar_http(metodo="GET", rota="/x", status=200, duracao_s=0.1)
        metricas_api.os_criada()
        metricas_api.os_duracao_status("recebida", 60.0)


# ---------------------------------------------------------------------------
# Flag desligada
# ---------------------------------------------------------------------------


class TestFlagDesligada:
    def test_flag_ausente_retorna_false_sem_importar_nada(
        self, monkeypatch: pytest.MonkeyPatch, facade_isolada: MetricasApi
    ) -> None:
        monkeypatch.delenv("API_METRICS_ENABLED", raising=False)
        # Import bloqueado: se o caminho off tentasse importar, o teste veria o
        # warning de dependencia ausente em vez de silencio.
        _bloquear_imports_otel(monkeypatch)
        app = FastAPI()
        rotas_antes = len(app.routes)

        with capture_logs() as logs:
            resultado = configurar_metricas_api(app)

        assert resultado is False
        assert logs == []
        # Nada montado, nenhum middleware, fachada segue no-op.
        assert len(app.routes) == rotas_antes
        assert app.user_middleware == []
        assert facade_isolada._http_duracao is None

    @pytest.mark.parametrize("valor", ["false", "False", "0", "", "off"])
    def test_valores_desligados_retornam_false(
        self, monkeypatch: pytest.MonkeyPatch, valor: str
    ) -> None:
        monkeypatch.setenv("API_METRICS_ENABLED", valor)
        _bloquear_imports_otel(monkeypatch)

        with capture_logs() as logs:
            resultado = configurar_metricas_api(FastAPI())

        assert resultado is False
        assert logs == []


# ---------------------------------------------------------------------------
# Flag ligada, extra ausente
# ---------------------------------------------------------------------------


class TestFlagLigadaSemDependencias:
    def test_retorna_false_e_loga_warning_acionavel(
        self, monkeypatch: pytest.MonkeyPatch, facade_isolada: MetricasApi
    ) -> None:
        monkeypatch.setenv("API_METRICS_ENABLED", "true")
        _bloquear_imports_otel(monkeypatch)
        app = FastAPI()

        with capture_logs() as logs:
            resultado = configurar_metricas_api(app)

        assert resultado is False
        warnings = [log for log in logs if log["log_level"] == "warning"]
        assert len(warnings) == 1
        # A mensagem precisa ser acionavel: dizer como instalar o extra.
        assert "--extra otel" in str(warnings[0])
        # Nada montado e fachada nao vinculada -> middleware/listener no-op.
        assert app.user_middleware == []
        assert facade_isolada._http_duracao is None


# ---------------------------------------------------------------------------
# Flag ligada, dependencias presentes (stubs)
# ---------------------------------------------------------------------------


class TestFlagLigadaComDependencias:
    def test_monta_provider_instrumentos_mount_e_middleware(
        self, monkeypatch: pytest.MonkeyPatch, otel_stubs: dict
    ) -> None:
        monkeypatch.setenv("API_METRICS_ENABLED", "true")
        monkeypatch.setenv("PYTSTOP_GIT_SHA", "abcdef0123456789")
        app = FastAPI()

        resultado = configurar_metricas_api(app)

        assert resultado is True
        # Resource identifica o servico no Prometheus.
        atributos = otel_stubs["resource_attributes"]
        assert atributos["service.name"] == "pytstop-api"
        assert atributos["service.version"] == "abcdef012345"  # sha [:12]
        # Meter nomeado pytstop-api; reader injetado no provider.
        assert otel_stubs["meter_nome"] == "pytstop-api"
        assert otel_stubs["metric_readers"] == [otel_stubs["reader"]]
        # NOMES EXATOS (contrato com os dashboards). http_request_duration
        # leva unit="s" (o exportador anexa -> http_request_duration_seconds);
        # pytstop_os_duracao_status_segundos NAO leva unit (evita o duplo
        # _segundos_seconds).
        assert set(otel_stubs["histogramas"]) == {
            "http_request_duration",
            "pytstop_os_duracao_status_segundos",
        }
        assert set(otel_stubs["counters"]) == {"pytstop_os_criadas_total"}
        assert otel_stubs["kwargs"]["http_request_duration"]["unit"] == "s"
        assert "unit" not in otel_stubs["kwargs"]["pytstop_os_duracao_status_segundos"]
        # Buckets adequados: latencia 5ms..5s; permanencia 1min..7dias.
        buckets_http = otel_stubs["kwargs"]["http_request_duration"][
            "explicit_bucket_boundaries_advisory"
        ]
        assert buckets_http[0] == 0.005
        assert buckets_http[-1] == 5.0
        buckets_status = otel_stubs["kwargs"]["pytstop_os_duracao_status_segundos"][
            "explicit_bucket_boundaries_advisory"
        ]
        assert buckets_status[0] == 60.0
        assert buckets_status[-1] == 604800.0
        # /metrics montado com o sub-app do prometheus_client.
        rotas_metrics = [
            r for r in app.routes if getattr(r, "path", None) == "/metrics"
        ]
        assert len(rotas_metrics) == 1
        # Middleware de latencia instalado.
        assert any(m.cls is MetricasHTTPMiddleware for m in app.user_middleware)

    def test_fachada_vinculada_usa_os_instrumentos_reais(
        self, monkeypatch: pytest.MonkeyPatch, otel_stubs: dict
    ) -> None:
        monkeypatch.setenv("API_METRICS_ENABLED", "true")

        assert configurar_metricas_api(FastAPI()) is True

        fachada = metrics_modulo.metricas_api
        fachada.os_criada()
        fachada.os_criada()
        fachada.os_duracao_status("recebida", 120.0)
        fachada.observar_http(
            metodo="GET", rota="/api/v1/ordens", status=200, duracao_s=0.05
        )

        assert otel_stubs["counters"]["pytstop_os_criadas_total"].total == 2
        (registro_status,) = otel_stubs["histogramas"][
            "pytstop_os_duracao_status_segundos"
        ].registros
        assert registro_status == (120.0, {"status": "recebida"})
        (registro_http,) = otel_stubs["histogramas"]["http_request_duration"].registros
        assert registro_http[0] == 0.05
        # Labels do contrato: method + rota (template) + status (string).
        assert registro_http[1] == {
            "method": "GET",
            "rota": "/api/v1/ordens",
            "status": "200",
        }


# ---------------------------------------------------------------------------
# Middleware HTTP (usa a fachada isolada com stubs vinculados na mao)
# ---------------------------------------------------------------------------


def _app_instrumentado(fachada: MetricasApi) -> FastAPI:
    """App minimo com rota parametrizada + rota que explode + middleware."""
    fachada._vincular(
        http_duracao=HistogramStub("http_request_duration"),
        os_criadas=CounterStub("pytstop_os_criadas_total"),
        os_duracao_status=HistogramStub("pytstop_os_duracao_status_segundos"),
    )
    app = FastAPI()

    @app.get("/itens/{item_id}")
    def obter_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    @app.get("/explode")
    def explode() -> None:
        raise RuntimeError("boom")

    app.add_middleware(MetricasHTTPMiddleware)
    return app


class TestMetricasHTTPMiddleware:
    def test_observa_rota_template_e_nao_o_path_bruto(
        self, facade_isolada: MetricasApi
    ) -> None:
        # Cardinalidade: o label rota e o TEMPLATE (/itens/{item_id}), nunca o
        # path concreto (/itens/42) — senao cada id viraria uma serie nova.
        app = _app_instrumentado(facade_isolada)
        client = TestClient(app)

        resp = client.get("/itens/42")

        assert resp.status_code == 200
        histograma = facade_isolada._http_duracao
        assert isinstance(histograma, HistogramStub)
        (registro,) = histograma.registros
        duracao, atributos = registro
        assert duracao > 0
        assert atributos == {
            "method": "GET",
            "rota": "/itens/{item_id}",
            "status": "200",
        }

    def test_path_sem_rota_casada_agrega_em_nao_roteada(
        self, facade_isolada: MetricasApi
    ) -> None:
        app = _app_instrumentado(facade_isolada)
        client = TestClient(app)

        resp = client.get("/caminho/inexistente/12345")

        assert resp.status_code == 404
        histograma = facade_isolada._http_duracao
        assert isinstance(histograma, HistogramStub)
        (registro,) = histograma.registros
        assert registro[1] == {
            "method": "GET",
            "rota": "nao_roteada",
            "status": "404",
        }

    def test_excecao_nao_tratada_conta_como_500_e_propaga(
        self, facade_isolada: MetricasApi
    ) -> None:
        app = _app_instrumentado(facade_isolada)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/explode")

        assert resp.status_code == 500
        histograma = facade_isolada._http_duracao
        assert isinstance(histograma, HistogramStub)
        (registro,) = histograma.registros
        assert registro[1] == {"method": "GET", "rota": "/explode", "status": "500"}
