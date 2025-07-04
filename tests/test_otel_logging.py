import unittest
import json
import logging
from io import StringIO
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from app.logger import setup_logging, get_logger, OtelJsonFormatter

class TestOpenTelemetryLogging(unittest.TestCase):
    """Test OpenTelemetry integration with structured JSON logging"""

    def setUp(self):
        """Setup test environment"""
        # Initialize OpenTelemetry
        trace.set_tracer_provider(TracerProvider())
        span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
        trace.get_tracer_provider().add_span_processor(span_processor)

        # Setup test logger with string buffer
        self.log_buffer = StringIO()
        self.test_logger = logging.getLogger("test-service")

        # Create formatter and handler
        formatter = OtelJsonFormatter(service_name="test-service")
        handler = logging.StreamHandler(self.log_buffer)
        handler.setFormatter(formatter)

        # Clear existing handlers and add our test handler
        self.test_logger.handlers = [handler]
        self.test_logger.setLevel(logging.INFO)

    def get_last_log_record(self):
        """Get the last log record as parsed JSON"""
        logs = self.log_buffer.getvalue().strip()
        if not logs:
            return None

        # Get the last line
        last_line = logs.split('\n')[-1]
        try:
            return json.loads(last_line)
        except json.JSONDecodeError:
            return None

    def test_basic_json_logging(self):
        """Test basic JSON log structure"""
        self.test_logger.info("Test message")

        log_record = self.get_last_log_record()
        self.assertIsNotNone(log_record)

        # Check required fields
        required_fields = ['timestamp', 'severity', 'service', 'TraceId', 'SpanId', 'ParentId', 'message']
        for field in required_fields:
            self.assertIn(field, log_record, f"Missing required field: {field}")

        # Check field values
        self.assertEqual(log_record['severity'], 'INFO')
        self.assertEqual(log_record['service'], 'test-service')
        self.assertEqual(log_record['message'], 'Test message')

    def test_logging_with_active_span(self):
        """Test logging within an active span"""
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("test-span") as span:
            span_context = span.get_span_context()
            expected_trace_id = f"{span_context.trace_id:032x}"
            expected_span_id = f"{span_context.span_id:016x}"

            self.test_logger.info("Message with span")

            log_record = self.get_last_log_record()
            self.assertIsNotNone(log_record)

            # Check OpenTelemetry fields are populated
            self.assertNotEqual(log_record['TraceId'], '')
            self.assertNotEqual(log_record['SpanId'], '')

            # TraceId and SpanId should be hex strings
            self.assertTrue(all(c in '0123456789abcdef' for c in log_record['TraceId'].lower()))
            self.assertTrue(all(c in '0123456789abcdef' for c in log_record['SpanId'].lower()))

            # For root span, ParentId should be empty
            self.assertEqual(log_record['ParentId'], '')

    def test_logging_with_nested_spans(self):
        """Test logging with nested spans (parent-child relationship)"""
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("parent-span") as parent_span:
            parent_context = parent_span.get_span_context()
            parent_span_id = f"{parent_context.span_id:016x}"

            # Clear buffer before child span
            self.log_buffer.seek(0)
            self.log_buffer.truncate(0)

            with tracer.start_as_current_span("child-span") as child_span:
                self.test_logger.info("Message from child span")

                log_record = self.get_last_log_record()
                self.assertIsNotNone(log_record)

                # Child span should have ParentId set to parent's SpanId
                self.assertEqual(log_record['ParentId'], parent_span_id)
                self.assertNotEqual(log_record['SpanId'], parent_span_id)

    def test_logging_without_span(self):
        """Test logging when no span is active"""
        # Make sure we're outside any span context
        from opentelemetry.context import detach, attach
        from opentelemetry import context

        # Clear any existing span context
        token = attach(context.set_value("current_span", None))

        try:
            self.test_logger.info("Message without span")

            log_record = self.get_last_log_record()
            self.assertIsNotNone(log_record)

            # Without active span, trace fields should be empty or default values
            # OpenTelemetry might return "0" or empty string when no span is active
            self.assertIn(log_record['TraceId'], ['', '0', '00000000000000000000000000000000'])
            self.assertIn(log_record['SpanId'], ['', '0', '0000000000000000'])
            self.assertEqual(log_record['ParentId'], '')
        finally:
            detach(token)

    def test_explicit_parent_id(self):
        """Test logging with explicitly set parent ID"""
        from app.logger import log_with_parent_span

        explicit_parent_id = "1234567890abcdef"
        log_with_parent_span(self.test_logger, "info", "Message with explicit parent", explicit_parent_id)

        log_record = self.get_last_log_record()
        self.assertIsNotNone(log_record)

        self.assertEqual(log_record['ParentId'], explicit_parent_id)

    def test_log_levels(self):
        """Test different log levels"""
        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

        for level in levels:
            self.log_buffer.seek(0)
            self.log_buffer.truncate(0)

            log_method = getattr(self.test_logger, level.lower())
            log_method(f"{level} message")

            log_record = self.get_last_log_record()
            if log_record:  # DEBUG might be filtered out
                self.assertEqual(log_record['severity'], level)

    def test_json_format_validity(self):
        """Test that all log messages are valid JSON"""
        messages = [
            "Simple message",
            "Message with 'quotes'",
            'Message with "double quotes"',
            "Message with\nnewlines",
            "Message with special chars: !@#$%^&*()",
        ]

        for msg in messages:
            self.log_buffer.seek(0)
            self.log_buffer.truncate(0)

            self.test_logger.info(msg)

            logs = self.log_buffer.getvalue().strip()
            self.assertTrue(logs, f"No log output for message: {msg}")

            # Should be valid JSON
            try:
                log_record = json.loads(logs)
                self.assertEqual(log_record['message'], msg)
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON for message '{msg}': {e}")


class TestOpenTelemetryIntegration(unittest.TestCase):
    """Test OpenTelemetry integration in the application"""

    def test_setup_logging_function(self):
        """Test the setup_logging function"""
        logger = setup_logging(service_name="test-app", log_level="DEBUG")

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test-app")

    def test_get_logger_function(self):
        """Test the get_logger function"""
        logger1 = get_logger("service-1")
        logger2 = get_logger("service-2")
        logger3 = get_logger()  # Default name

        self.assertEqual(logger1.name, "service-1")
        self.assertEqual(logger2.name, "service-2")
        self.assertEqual(logger3.name, "mcp-server")

        # Should return the same logger instance for the same name
        logger1_again = get_logger("service-1")
        self.assertIs(logger1, logger1_again)


if __name__ == '__main__':
    unittest.main()
