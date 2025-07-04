import logging
import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pythonjsonlogger import jsonlogger


class OtelJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds OpenTelemetry fields and service name"""

    def __init__(self, *args, service_name: str = "mcp-server", **kwargs):
        self.service_name = service_name
        # Define the format string with all required fields
        fmt = '%(asctime)s %(levelname)s %(name)s %(otelTraceID)s %(otelSpanID)s %(otelParentID)s %(service)s %(message)s'
        super().__init__(fmt, *args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to the log record"""
        super().add_fields(log_record, record, message_dict)

        # Add service name
        log_record['service'] = self.service_name

        # Rename timestamp field
        if 'asctime' in log_record:
            log_record['timestamp'] = log_record.pop('asctime')

        # Rename severity field
        if 'levelname' in log_record:
            log_record['severity'] = log_record.pop('levelname')

        # Ensure OpenTelemetry fields are present with proper names
        trace_id = getattr(record, 'otelTraceID', '')
        span_id = getattr(record, 'otelSpanID', '')

        # Format trace and span IDs properly (remove 0x prefix if present)
        log_record['TraceId'] = trace_id.replace('0x', '') if trace_id else ''
        log_record['SpanId'] = span_id.replace('0x', '') if span_id else ''

        # Handle ParentId - try to get from current span context
        parent_id = ''
        try:
            current_span = trace.get_current_span()
            if current_span and hasattr(current_span, 'parent') and current_span.parent:
                parent_id = f"{current_span.parent.span_id:016x}"
        except Exception:
            pass

        log_record['ParentId'] = getattr(record, 'otelParentID', parent_id)

        # Clean up original otel fields
        for field in ['otelTraceID', 'otelSpanID', 'otelParentID']:
            log_record.pop(field, None)


def setup_logging(service_name: str = "mcp-server", log_level: str = "INFO") -> logging.Logger:
    """Setup structured JSON logging with OpenTelemetry integration"""

    # Enable OpenTelemetry log correlation
    os.environ.setdefault('OTEL_PYTHON_LOG_CORRELATION', 'true')

    # Instrument logging to add OpenTelemetry fields
    LoggingInstrumentor().instrument(set_logging_format=False)

    # Create custom formatter
    formatter = OtelJsonFormatter(
        service_name=service_name,
        datefmt='%Y-%m-%dT%H:%M:%S'  # Fixed: no %f
    )

    # Set up handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Return logger for the service
    logger = logging.getLogger(service_name)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get logger instance with OpenTelemetry integration"""
    logger_name = name or "mcp-server"
    return logging.getLogger(logger_name)


def log_with_parent_span(logger: logging.Logger, level: str, message: str, parent_span_id: Optional[str] = None):
    """Log message with explicit parent span ID"""
    extra = {}
    if parent_span_id:
        extra['otelParentID'] = parent_span_id

    log_method = getattr(logger, level.lower())
    log_method(message, extra=extra)


# Initialize default logger
logger = setup_logging()
