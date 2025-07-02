import httpx
from app.config import settings

async def handle_request(data: dict) -> list:
    """
    Fetch comments for a given post ID.
    Expects: {"post_id": <int>}
    """
    post_id = data.get("post_id")
    url = f"{settings.jsonplaceholder_base_url}/comments"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params={"postId": post_id}, timeout=5.0)
        resp.raise_for_status()
        return resp.json()
