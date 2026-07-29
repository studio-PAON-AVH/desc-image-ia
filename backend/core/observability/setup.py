"""Bootstrap OpenTelemetry commun à l'API et au worker.

Configure les trois signaux (traces, métriques, logs) avec export OTLP vers
la stack LGTM (service `lgtm` du docker-compose), plus les instrumentations
automatiques FastAPI / SQLAlchemy / Redis / httpx / requests.

L'observabilité n'est activée que si OTEL_EXPORTER_OTLP_ENDPOINT est défini
(et que OTEL_SDK_DISABLED n'est pas "true") : en local ou pendant les tests,
sans collecteur, le SDK reste inerte et n'émet aucune erreur de connexion.
"""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_configured = False


def _enabled() -> bool:
    if os.getenv("OTEL_SDK_DISABLED", "").strip().lower() == "true":
        return False
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))


def _exporters():
    """Sélectionne les exporters OTLP selon OTEL_EXPORTER_OTLP_PROTOCOL.

    grpc (défaut, endpoint :4317) en prod/Docker. En dev local avec
    uvicorn --reload, gRPC crache des warnings au fork ("skipping fork()
    handlers") : mettre OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf (endpoint
    :4318) bascule sur l'export HTTP, sans thread gRPC, donc sans ce bruit.
    """
    protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").strip().lower()
    if protocol in ("http/protobuf", "http/json", "http"):
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    else:
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    return OTLPSpanExporter, OTLPMetricExporter, OTLPLogExporter


def setup_observability(service_name: str, app=None) -> None:
    """Initialise traces, métriques et logs OTel pour le processus courant.

    À appeler une seule fois par processus : depuis main.py pour l'API (avec
    `app` pour instrumenter FastAPI), depuis l'événement WORKER_STARTUP pour
    le worker taskiq. Les instruments créés avant cet appel via l'API globale
    (metric.py, otel_taskiq.py) sont re-liés automatiquement par les proxys
    OTel, l'ordre d'import n'a donc pas d'importance.
    """
    global _configured
    if not _enabled():
        logger.info("OpenTelemetry désactivé (OTEL_EXPORTER_OTLP_ENDPOINT absent)")
        return
    if _configured:
        return
    _configured = True

    resource = Resource.create({"service.name": service_name})
    OTLPSpanExporter, OTLPMetricExporter, OTLPLogExporter = _exporters()

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    # Métriques
    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

    # Logs : tout ce qui passe par le logging stdlib part vers Loki, corrélé
    # automatiquement au trace_id/span_id courant.
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(logger_provider)
    root = logging.getLogger()
    root.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))
    if root.level == logging.NOTSET or root.level > logging.INFO:
        root.setLevel(logging.INFO)

    _instrument_libraries(app)
    logger.info("OpenTelemetry initialisé pour le service %s", service_name)


def _instrument_libraries(app) -> None:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor

    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    # CPU/mémoire du process (et du host) : exportées en OTLP comme le reste,
    # aucun collecteur externe (cAdvisor/node-exporter) n'est nécessaire.
    SystemMetricsInstrumentor().instrument()

    # Le moteur async est créé à l'import de core.database.config, donc avant
    # ce setup : il faut l'instrumenter explicitement (l'instrumentation
    # globale ne couvre que les moteurs créés après coup). asyncpg n'est pas
    # instrumenté en plus, ça dupliquerait chaque requête dans les traces.
    try:
        from ..database.config import engine

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    except Exception as exc:
        logger.warning("Instrumentation SQLAlchemy impossible: %s", exc)

    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        # /health est sondé toutes les 10s par le healthcheck Docker : exclu
        # pour ne pas noyer Tempo.
        FastAPIInstrumentor.instrument_app(app, excluded_urls="/health")
