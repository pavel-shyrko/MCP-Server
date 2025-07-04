from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
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

    @property
    def system_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_file = Path(__file__).parent / "prompts" / "system_prompt.txt"
        return prompt_file.read_text(encoding="utf-8").strip()

    class Config:
        # Check for --env-file argument first, then ENV_FILE, then default
        env_file = None
        env_file_encoding = "utf-8"

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_settings):
            # Check command line arguments for --env-file
            env_file = ".env.local"  # default
            if "--env-file" in sys.argv:
                try:
                    idx = sys.argv.index("--env-file")
                    env_file = sys.argv[idx + 1]
                except (IndexError, ValueError):
                    pass
            else:
                env_file = os.getenv("ENV_FILE", ".env.local")

            cls.env_file = env_file
            return init_settings, env_settings, file_settings

settings = Settings()
