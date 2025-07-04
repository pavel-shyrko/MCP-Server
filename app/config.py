from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from pydantic import ConfigDict  # Import ConfigDict for Pydantic v2
import os
import sys
from pathlib import Path

class Settings(BaseSettings):
    """
    Central configuration for all base URLs and endpoints.
    """
    # Ollama chat API
    llm_base_url: AnyHttpUrl = "http://host.docker.internal:11434"
    # This FastAPI server (for dispatching to our tool endpoints)
    local_api_base: AnyHttpUrl = "http://127.0.0.1:8080"
    # JSONPlaceholder public API
    jsonplaceholder_base_url: AnyHttpUrl = "https://jsonplaceholder.typicode.com"
    # Paths for our two tools
    post_tool_path: str = "post-call"
    comments_tool_path: str = "comments-call"

    @field_validator('llm_base_url', 'local_api_base', 'jsonplaceholder_base_url')
    @classmethod
    def normalize_urls(cls, v):
        """Remove trailing slash from URLs to ensure consistency"""
        if isinstance(v, str):
            return v.rstrip('/')
        return str(v).rstrip('/')

    @property
    def system_prompt(self) -> str:
        """Load system prompt from file"""
        try:
            prompt_file = Path(__file__).parent / "prompts" / "system_prompt.txt"
            if not prompt_file.exists():
                raise FileNotFoundError(f"System prompt file not found: {prompt_file}")
            return prompt_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            # Return a default prompt if file loading fails
            return "You are a helpful AI assistant that can fetch posts and comments from JSONPlaceholder API."

    # Use ConfigDict instead of class Config
    model_config = ConfigDict(
        env_file=None,
        env_file_encoding="utf-8"
    )

    @classmethod
    def customise_sources(cls, init_settings, env_settings, file_settings):
        """Customizes the sources for environment variables and config files."""
        env_file = ".env.local"  # default
        if "--env-file" in sys.argv:
            try:
                idx = sys.argv.index("--env-file")
                env_file = sys.argv[idx + 1]
            except (IndexError, ValueError):
                pass
        else:
            env_file = os.getenv("ENV_FILE", ".env.local")
        cls.model_config["env_file"] = env_file
        return init_settings, env_settings, file_settings

settings = Settings()
