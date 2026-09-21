"""OpenTelemetry tracing configuration."""

from fastapi import FastAPI

from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except Exception:
    trace = None
    Status = None
    StatusCode = None
    OTEL_AVAILABLE = False


def setup_tracing(app: FastAPI) -> None:
    """Setup OpenTelemetry tracing."""
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry is disabled")
        return

    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry core libraries not available")
        return

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource
        resource = Resource(attributes={
            SERVICE_NAME: settings.OTEL_SERVICE_NAME,
            "service.version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
        })

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )

        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=tracer_provider,
        )

        logger.info("OpenTelemetry tracing enabled")

    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")


def get_tracer(name: str = "agentshield") -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def create_span(name: str, attributes: dict = None):
    """Create a span decorator."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator


def trace_function(name: str = None, attributes: dict = None):
    """Decorator for tracing functions."""
    def decorator(func):
        span_name = name or func.__name__
        return create_span(span_name, attributes)(func)
    return decorator


class SpanContext:
    """Context manager for spans."""

    def __init__(self, name: str, attributes: dict = None):
        self.name = name
        self.attributes = attributes or {}
        self.span = None

    async def __aenter__(self):
        tracer = get_tracer()
        self.span = tracer.start_span(self.name)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        self.span.__enter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))
        self.span.__exit__(exc_type, exc_val, exc_tb)
        self.span.end()
