import unittest
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.llm_agent import (
    run_agent,
    AgentError,
    LLMConnectionError,
    LLMResponseError,
    ToolDispatchError
)
import warnings

# Suppress warnings for tests
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


class TestLLMAgent(unittest.TestCase):
    """Test LLM Agent functionality"""

    def setUp(self):
        """Setup test environment"""
        self.test_query = "Get me post number two"
        self.mock_settings = MagicMock()
        self.mock_settings.system_prompt = "Test system prompt"
        self.mock_settings.llm_base_url = "http://localhost:11434"
        self.mock_settings.local_api_base = "http://localhost:8080"

    @patch('app.llm_agent.settings')
    @patch('app.llm_agent.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_successful_agent_execution(self, mock_client, mock_settings):
        """Test successful agent execution flow"""
        mock_settings.return_value = self.mock_settings

        # Mock Ollama response
        mock_ollama_response = MagicMock()
        mock_ollama_response.status_code = 200
        mock_ollama_response.text = '{"message": {"content": "{\\"tool\\": \\"post_call\\", \\"args\\": {\\"post_id\\": 2}}"}}\n'
        mock_ollama_response.raise_for_status = MagicMock()

        # Mock tool response
        mock_tool_response = MagicMock()
        mock_tool_response.status_code = 200
        mock_tool_response.json.return_value = {"id": 2, "title": "Test Post"}
        mock_tool_response.raise_for_status = MagicMock()

        # Setup mock client
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = [mock_ollama_response, mock_tool_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await run_agent(self.test_query)

        self.assertEqual(result, {"id": 2, "title": "Test Post"})
        self.assertEqual(mock_client_instance.post.call_count, 2)

    @patch('app.llm_agent.settings')
    @patch('app.llm_agent.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_llm_connection_error(self, mock_client, mock_settings):
        """Test LLM connection error handling"""
        mock_settings.return_value = self.mock_settings

        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.TimeoutException("Connection timeout")
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with self.assertRaises(LLMConnectionError) as context:
            await run_agent(self.test_query)

        self.assertIn("Timeout connecting to LLM service", str(context.exception))

    @patch('app.llm_agent.settings')
    @patch('app.llm_agent.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_invalid_llm_response(self, mock_client, mock_settings):
        """Test invalid LLM response handling"""
        mock_settings.return_value = self.mock_settings

        # Mock invalid JSON response
        mock_ollama_response = MagicMock()
        mock_ollama_response.status_code = 200
        mock_ollama_response.text = '{"message": {"content": "invalid json"}}\n'
        mock_ollama_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_ollama_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with self.assertRaises(LLMResponseError) as context:
            await run_agent(self.test_query)

        self.assertIn("Invalid JSON in LLM response", str(context.exception))

    @patch('app.llm_agent.settings')
    @patch('app.llm_agent.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_tool_dispatch_error(self, mock_client, mock_settings):
        """Test tool dispatch error handling"""
        mock_settings.return_value = self.mock_settings

        # Mock valid Ollama response
        mock_ollama_response = MagicMock()
        mock_ollama_response.status_code = 200
        mock_ollama_response.text = '{"message": {"content": "{\\"tool\\": \\"post_call\\", \\"args\\": {\\"post_id\\": 2}}"}}\n'
        mock_ollama_response.raise_for_status = MagicMock()

        # Mock tool 404 error
        mock_tool_response = MagicMock()
        mock_tool_response.status_code = 404

        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = [mock_ollama_response, mock_tool_response]
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with self.assertRaises(ToolDispatchError) as context:
            await run_agent(self.test_query)

        self.assertIn("Tool 'post_call' not found", str(context.exception))

    @patch('app.llm_agent.settings')
    @patch('app.llm_agent.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_empty_llm_response(self, mock_client, mock_settings):
        """Test empty LLM response handling"""
        mock_settings.return_value = self.mock_settings

        mock_ollama_response = MagicMock()
        mock_ollama_response.status_code = 200
        mock_ollama_response.text = ""
        mock_ollama_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_ollama_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with self.assertRaises(LLMResponseError) as context:
            await run_agent(self.test_query)

        self.assertIn("LLM returned empty response", str(context.exception))

    @patch('app.llm_agent.settings')
    @patch('app.llm_agent.httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_missing_tool_field(self, mock_client, mock_settings):
        """Test missing tool field in LLM response"""
        mock_settings.return_value = self.mock_settings

        mock_ollama_response = MagicMock()
        mock_ollama_response.status_code = 200
        mock_ollama_response.text = '{"message": {"content": "{\\"args\\": {\\"post_id\\": 2}}"}}\n'
        mock_ollama_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_ollama_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with self.assertRaises(LLMResponseError) as context:
            await run_agent(self.test_query)

        self.assertIn("Missing 'tool' key in response", str(context.exception))


if __name__ == '__main__':
    unittest.main()
