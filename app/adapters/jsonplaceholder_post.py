import httpx
from app.config import settings

async def handle_request(data: dict) -> dict:
    """
    Fetch a post by ID from JSONPlaceholder.
    Expects: {"post_id": <int>}
    """
    post_id = data.get("post_id")
    url = f"{settings.jsonplaceholder_base_url}/posts/{post_id}"
    # Disable SSL verification for development (Windows certificate issues)
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(url, timeout=5.0)
        resp.raise_for_status()
        return resp.json()
