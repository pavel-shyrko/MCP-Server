# Tests for MCP Server

This directory contains all unit tests for the MCP Server project.

## Structure

- `test_otel_logging.py` - OpenTelemetry logging integration tests
- `test_llm_agent.py` - LLM agent functionality tests  
- `test_adapters.py` - Adapter tests for external API integrations
- `test_router.py` - FastAPI router endpoint tests
- `test_config.py` - Configuration management tests

## Running Tests

Run all tests:
```bash
python -m pytest tests/ -v
```

Run specific test file:
```bash
python -m pytest tests/test_otel_logging.py -v
```

Run with coverage:
```bash
python -m pytest tests/ --cov=app --cov-report=html
```

## Test Requirements

Additional test dependencies can be installed:
```bash
pip install pytest pytest-asyncio pytest-cov
```
