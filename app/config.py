from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

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
    system_prompt: str = """
    You have two tools you can call:
    1) post_call — Fetch a post. Args schema: {"post_id": <integer>}.
    2) comments_call — Fetch comments for a post. Args schema: {"post_id": <integer>}.

    When the user asks for information:
    - Output *only* valid JSON with exactly keys "tool" and "args".
    - "tool" must be either "post_call" or "comments_call".
    - "args" must follow the schema above.

    Do not output any extra text, only the JSON.
    """

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
