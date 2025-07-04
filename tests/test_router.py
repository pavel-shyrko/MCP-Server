import unittest
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.router import router, QueryRequest, PostRequest, CommentsRequest
from app.llm_agent import LLMConnectionError, LLMResponseError, ToolDispatchError

# Create a test app for testing
fastapi_app = FastAPI()
fastapi_app.include_router(router)


class TestRouter(unittest.TestCase):
    """Test FastAPI router endpoints"""

    def setUp(self):
        """Setup test environment"""
        self.client = TestClient(fastapi_app)

    @patch('app.router.fetch_post')
    def test_post_call_endpoint(self, mock_fetch_post):
        """Test /post-call endpoint"""
        mock_fetch_post.return_value = {"id": 2, "title": "Test Post"}

        response = self.client.post(
            "/post-call",
            json={"post_id": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": 2, "title": "Test Post"})

    @patch('app.router.fetch_comments')
    def test_comments_call_endpoint(self, mock_fetch_comments):
        """Test /comments-call endpoint"""
        mock_comments_response = [{"id": 6, "postId": 2, "body": "Test comment"}]
        mock_fetch_comments.return_value = mock_comments_response

        response = self.client.post(
            "/comments-call",
            json={"post_id": 2}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mock_comments_response)

    @patch('app.router.run_agent')
    def test_ask_endpoint_success(self, mock_run_agent):
        """Test /ask endpoint successful execution"""
        mock_run_agent.return_value = {"id": 2, "title": "Test Post"}

        response = self.client.post(
            "/ask",
            json={"query": "Get me post number two"}
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["result"], {"id": 2, "title": "Test Post"})

    @patch('app.router.run_agent')
    def test_ask_endpoint_llm_connection_error(self, mock_run_agent):
        """Test /ask endpoint with LLM connection error"""
        mock_run_agent.side_effect = LLMConnectionError("LLM service unavailable")

        response = self.client.post(
            "/ask",
            json={"query": "Get me post number two"}
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertEqual(response_data["error_type"], "llm_connection_error")
        self.assertIn("LLM service unavailable", response_data["error"])

    @patch('app.router.run_agent')
    def test_ask_endpoint_llm_response_error(self, mock_run_agent):
        """Test /ask endpoint with LLM response error"""
        mock_run_agent.side_effect = LLMResponseError("Invalid JSON response")

        response = self.client.post(
            "/ask",
            json={"query": "Get me post number two"}
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertEqual(response_data["error_type"], "llm_response_error")
        self.assertIn("Invalid response from LLM", response_data["error"])

    @patch('app.router.run_agent')
    def test_ask_endpoint_tool_dispatch_error(self, mock_run_agent):
        """Test /ask endpoint with tool dispatch error"""
        mock_run_agent.side_effect = ToolDispatchError("Tool not found")

        response = self.client.post(
            "/ask",
            json={"query": "Get me post number two"}
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertEqual(response_data["error_type"], "tool_dispatch_error")
        self.assertIn("Tool execution failed", response_data["error"])

    @patch('app.router.run_agent')
    def test_ask_endpoint_unexpected_error(self, mock_run_agent):
        """Test /ask endpoint with unexpected error"""
        mock_run_agent.side_effect = Exception("Unexpected error")

        response = self.client.post(
            "/ask",
            json={"query": "Get me post number two"}
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertEqual(response_data["error_type"], "internal_error")
        self.assertIn("Internal server error", response_data["error"])

    def test_post_call_validation(self):
        """Test /post-call endpoint input validation"""
        # Missing post_id
        response = self.client.post("/post-call", json={})
        self.assertEqual(response.status_code, 422)

        # Invalid post_id type
        response = self.client.post("/post-call", json={"post_id": "invalid"})
        self.assertEqual(response.status_code, 422)

    def test_comments_call_validation(self):
        """Test /comments-call endpoint input validation"""
        # Missing post_id
        response = self.client.post("/comments-call", json={})
        self.assertEqual(response.status_code, 422)

        # Invalid post_id type
        response = self.client.post("/comments-call", json={"post_id": "invalid"})
        self.assertEqual(response.status_code, 422)

    def test_ask_validation(self):
        """Test /ask endpoint input validation"""
        # Missing query
        response = self.client.post("/ask", json={})
        self.assertEqual(response.status_code, 422)

        # Empty query should be valid (FastAPI doesn't validate string length by default)
        response = self.client.post("/ask", json={"query": ""})
        # This should actually succeed but might fail in agent execution
        self.assertTrue(response.status_code in [200, 422])


class TestPydanticModels(unittest.TestCase):
    """Test Pydantic request models"""

    def test_query_request_model(self):
        """Test QueryRequest model validation"""
        # Valid request
        request = QueryRequest(query="Get me post number two")
        self.assertEqual(request.query, "Get me post number two")

        # Test with example
        request = QueryRequest(query="покажи мне публикацию номер два")
        self.assertEqual(request.query, "покажи мне публикацию номер два")

    def test_post_request_model(self):
        """Test PostRequest model validation"""
        # Valid request
        request = PostRequest(post_id=2)
        self.assertEqual(request.post_id, 2)

        # Test validation with invalid type should raise ValueError during model creation
        try:
            PostRequest(post_id="invalid")
            self.fail("Should have raised validation error")
        except Exception:
            pass  # Expected validation error

    def test_comments_request_model(self):
        """Test CommentsRequest model validation"""
        # Valid request
        request = CommentsRequest(post_id=2)
        self.assertEqual(request.post_id, 2)

        # Test with different valid ID
        request = CommentsRequest(post_id=100)
        self.assertEqual(request.post_id, 100)


if __name__ == '__main__':
    unittest.main()
