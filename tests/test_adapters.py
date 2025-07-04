import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.adapters.jsonplaceholder_post import handle_request as handle_post_request
from app.adapters.jsonplaceholder_comments import handle_request as handle_comments_request

class TestPostAdapter(unittest.IsolatedAsyncioTestCase):
    """Test JSONPlaceholder Post adapter"""

    def setUp(self):
        """Setup test environment"""
        self.valid_data = {"post_id": 2}
        self.mock_post_response = {
            "userId": 1,
            "id": 2,
            "title": "qui est esse",
            "body": "est rerum tempore vitae"
        }

    @patch('app.adapters.jsonplaceholder_post.httpx.AsyncClient')
    @patch('app.adapters.jsonplaceholder_post.settings')
    async def test_successful_post_fetch(self, mock_settings, mock_client):
        """Test successful post fetching"""
        mock_settings.jsonplaceholder_base_url = "https://jsonplaceholder.typicode.com"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_post_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await handle_post_request(self.valid_data)

        self.assertEqual(result, self.mock_post_response)
        mock_client_instance.get.assert_called_once()

    async def test_missing_post_id(self):
        """Test missing post_id parameter"""
        with self.assertRaises(ValueError) as context:
            await handle_post_request({})

        self.assertIn("post_id is required", str(context.exception))

    async def test_invalid_post_id_type(self):
        """Test invalid post_id type"""
        invalid_data = {"post_id": "not_a_number"}

        with self.assertRaises(ValueError) as context:
            await handle_post_request(invalid_data)

        self.assertIn("post_id must be a positive integer", str(context.exception))

    async def test_negative_post_id(self):
        """Test negative post_id"""
        invalid_data = {"post_id": -5}

        with self.assertRaises(ValueError) as context:
            await handle_post_request(invalid_data)

        self.assertIn("post_id must be a positive integer", str(context.exception))

    @patch('app.adapters.jsonplaceholder_post.httpx.AsyncClient')
    @patch('app.adapters.jsonplaceholder_post.settings')
    async def test_post_not_found(self, mock_settings, mock_client):
        """Test 404 post not found"""
        mock_settings.jsonplaceholder_base_url = "https://jsonplaceholder.typicode.com"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with self.assertRaises(ValueError) as context:
            await handle_post_request(self.valid_data)

        self.assertIn("not found", str(context.exception))

    @patch('app.adapters.jsonplaceholder_post.httpx.AsyncClient')
    @patch('app.adapters.jsonplaceholder_post.settings')
    async def test_network_timeout(self, mock_settings, mock_client):
        """Test network timeout handling"""
        mock_settings.jsonplaceholder_base_url = "https://jsonplaceholder.typicode.com"

        mock_client_instance = AsyncMock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("timeout")
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        with self.assertRaises(RuntimeError) as context:
            await handle_post_request(self.valid_data)

        self.assertIn("Timeout while fetching post", str(context.exception))


class TestCommentsAdapter(unittest.IsolatedAsyncioTestCase):
    """Test JSONPlaceholder Comments adapter"""

    def setUp(self):
        """Setup test environment"""
        self.valid_data = {"post_id": 2}
        self.mock_comments_response = [
            {
                "postId": 2,
                "id": 6,
                "name": "et fugit eligendi deleniti quidem qui sint nihil autem",
                "email": "Presley.Mueller@myrl.com",
                "body": "doloribus at sed quis culpa deserunt consectetur qui praesentium"
            },
            {
                "postId": 2,
                "id": 7,
                "name": "repellat consequatur praesentium vel minus molestias voluptatum",
                "email": "Dallas@ole.me",
                "body": "maiores sed dolores similique labore et inventore et"
            }
        ]

    @patch('app.adapters.jsonplaceholder_comments.httpx.AsyncClient')
    @patch('app.adapters.jsonplaceholder_comments.settings')
    async def test_successful_comments_fetch(self, mock_settings, mock_client):
        """Test successful comments fetching"""
        mock_settings.jsonplaceholder_base_url = "https://jsonplaceholder.typicode.com"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_comments_response
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        result = await handle_comments_request(self.valid_data)

        self.assertEqual(result, self.mock_comments_response)
        mock_client_instance.get.assert_called_once()

    async def test_missing_post_id(self):
        """Test missing post_id parameter"""
        with self.assertRaises(ValueError) as context:
            await handle_comments_request({})

        self.assertIn("post_id is required", str(context.exception))

    async def test_invalid_response_type(self):
        """Test invalid response type (not a list)"""
        with patch('app.adapters.jsonplaceholder_comments.httpx.AsyncClient') as mock_client, \
             patch('app.adapters.jsonplaceholder_comments.settings') as mock_settings:
            mock_settings.jsonplaceholder_base_url = "https://jsonplaceholder.typicode.com"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"unexpected": "dict"}
            mock_response.raise_for_status = MagicMock()
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            with self.assertRaises(TypeError) as context:
                await handle_comments_request(self.valid_data)
            self.assertIn("list", str(context.exception))

    async def test_empty_comments_list(self):
        """Test empty comments list"""
        with patch('app.adapters.jsonplaceholder_comments.httpx.AsyncClient') as mock_client, \
             patch('app.adapters.jsonplaceholder_comments.settings') as mock_settings:
            mock_settings.jsonplaceholder_base_url = "https://jsonplaceholder.typicode.com"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_response.raise_for_status = MagicMock()
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            result = await handle_comments_request(self.valid_data)
            self.assertEqual(result, [])
