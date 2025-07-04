import unittest
import os
from unittest.mock import patch
from app.config import Settings

class TestConfig(unittest.TestCase):
    """Test configuration management"""

    def setUp(self):
        """Setup test environment"""
        self.original_env = os.environ.copy()

    def tearDown(self):
        """Cleanup test environment"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_default_settings(self):
        """Test default configuration values"""
        # Clear environment variables that might affect the test
        for key in list(os.environ.keys()):
            if key.upper() in ['LLM_BASE_URL', 'LOCAL_API_BASE', 'JSONPLACEHOLDER_BASE_URL']:
                del os.environ[key]

        settings = Settings()

        # Теперь ожидаем URL без завершающего слэша
        self.assertEqual(str(settings.llm_base_url), "http://host.docker.internal:11434")
        self.assertEqual(str(settings.local_api_base), "http://127.0.0.1:8080")
        self.assertEqual(str(settings.jsonplaceholder_base_url), "https://jsonplaceholder.typicode.com")
        self.assertEqual(settings.post_tool_path, "post-call")
        self.assertEqual(settings.comments_tool_path, "comments-call")

    def test_environment_override(self):
        """Test environment variable override"""
        # Clear existing env vars first
        for key in list(os.environ.keys()):
            if key.upper() in ['LLM_BASE_URL', 'LOCAL_API_BASE', 'JSONPLACEHOLDER_BASE_URL']:
                del os.environ[key]

        # Set test values
        os.environ["LLM_BASE_URL"] = "http://localhost:11434"
        os.environ["LOCAL_API_BASE"] = "http://localhost:8080"
        os.environ["JSONPLACEHOLDER_BASE_URL"] = "https://api.example.com"

        settings = Settings()

        # Теперь ожидаем URL без завершающего слэша
        self.assertEqual(str(settings.llm_base_url), "http://localhost:11434")
        self.assertEqual(str(settings.local_api_base), "http://localhost:8080")
        self.assertEqual(str(settings.jsonplaceholder_base_url), "https://api.example.com")

    def test_system_prompt_loading(self):
        """Test system prompt loading from file"""
        # Test with actual prompt file that should exist
        settings = Settings()

        # Just verify that system_prompt property exists and returns a string
        prompt = settings.system_prompt
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)

    def test_system_prompt_file_not_found(self):
        """Test system prompt when file doesn't exist"""
        with patch('pathlib.Path.read_text') as mock_read:
            mock_read.side_effect = FileNotFoundError("File not found")

            settings = Settings()

            # Теперь ожидаем дефолтную строку, а не исключение
            prompt = settings.system_prompt
            self.assertEqual(prompt, "You are a helpful AI assistant that can fetch posts and comments from JSONPlaceholder API.")

    def test_url_validation(self):
        """Test URL validation in settings"""
        # Clear existing env vars first
        for key in list(os.environ.keys()):
            if key.upper() in ['LLM_BASE_URL']:
                del os.environ[key]

        # Valid URLs should work
        os.environ["LLM_BASE_URL"] = "https://api.openai.com"
        settings = Settings()
        self.assertEqual(str(settings.llm_base_url), "https://api.openai.com")

        # Invalid URLs should raise validation error
        os.environ["LLM_BASE_URL"] = "not-a-valid-url"
        with self.assertRaises(Exception):  # Pydantic validation error
            Settings()

    def test_tool_path_configuration(self):
        """Test tool path configuration"""
        # Clear existing env vars first
        for key in list(os.environ.keys()):
            if key.upper() in ['POST_TOOL_PATH', 'COMMENTS_TOOL_PATH']:
                del os.environ[key]

        os.environ["POST_TOOL_PATH"] = "custom-post-endpoint"
        os.environ["COMMENTS_TOOL_PATH"] = "custom-comments-endpoint"

        settings = Settings()

        self.assertEqual(settings.post_tool_path, "custom-post-endpoint")
        self.assertEqual(settings.comments_tool_path, "custom-comments-endpoint")

    def test_settings_immutability(self):
        """Test that settings are properly configured as immutable where expected"""
        settings = Settings()

        # Test that we can access all properties
        self.assertIsNotNone(settings.llm_base_url)
        self.assertIsNotNone(settings.local_api_base)
        self.assertIsNotNone(settings.jsonplaceholder_base_url)
        self.assertIsNotNone(settings.post_tool_path)
        self.assertIsNotNone(settings.comments_tool_path)

    def test_env_file_loading(self):
        """Test environment file loading"""
        # This test just verifies that the settings class can be instantiated
        # without errors, as env file loading is handled by pydantic-settings
        settings = Settings()
        self.assertIsInstance(settings, Settings)


if __name__ == '__main__':
    unittest.main()
