import os
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from app.logger import setup_logging, get_logger
from app.router import router

# Initialize OpenTelemetry
def setup_telemetry():
    """Setup OpenTelemetry tracing"""
    # Set service name
    os.environ.setdefault('OTEL_SERVICE_NAME', 'mcp-server')

    # Initialize tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # Add console exporter for development
    span_processor = BatchSpanProcessor(ConsoleSpanExporter())
    trace.get_tracer_provider().add_span_processor(span_processor)

    return tracer

# Setup telemetry and logging before creating FastAPI app
tracer = setup_telemetry()
logger = setup_logging(service_name="mcp-server", log_level="INFO")

app = FastAPI(
    title="MCP Server",
    description="AI access to secure internal systems",
    version="0.1.0"
)

# Instrument FastAPI and HTTPX
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

app.include_router(router)

logger.info("MCP Server initialized with OpenTelemetry support")
