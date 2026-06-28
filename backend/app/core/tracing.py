from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from typing import Any

from fastapi import FastAPI

from app.core.config import get_settings

_configured = False


def configure_tracing(app: FastAPI | None = None, engine: Any | None = None) -> None:
    settings = get_settings()
    if not settings.otel_enabled:
        return

    global _configured
    if _configured:
        if app:
            _instrument_fastapi(app)
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError as exc:
        raise RuntimeError("OpenTelemetry dependencies are required when OTEL_ENABLED=true") from exc

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": settings.otel_service_name,
                "deployment.environment": settings.environment,
            }
        )
    )
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint) if settings.otel_exporter_otlp_endpoint else ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if app:
        FastAPIInstrumentor.instrument_app(app)
    if engine:
        SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    _configured = True


@contextmanager
def traced_span(name: str, **attributes: Any) -> Iterator[None]:
    settings = get_settings()
    if not settings.otel_enabled:
        with nullcontext():
            yield
        return
    try:
        from opentelemetry import trace
    except ImportError:
        with nullcontext():
            yield
        return

    tracer = trace.get_tracer(settings.otel_service_name)
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield


def _instrument_fastapi(app: FastAPI) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        return
    FastAPIInstrumentor.instrument_app(app)
