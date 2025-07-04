import httpx
from app.config import settings
from app.logger import logger

async def handle_request(data: dict) -> dict:
    """
    Fetch a post by ID from JSONPlaceholder.
    Expects: {"post_id": <int>}
    """
    post_id = data.get("post_id")

    if post_id is None:
        logger.error("[POST-ADAPTER] Missing post_id in request data")
        raise ValueError("post_id is required")

    if not isinstance(post_id, int) or post_id <= 0:
        logger.error(f"[POST-ADAPTER] Invalid post_id: {post_id}")
        raise ValueError(f"post_id must be a positive integer, got: {post_id}")

    url = f"{settings.jsonplaceholder_base_url}/posts/{post_id}"
    logger.info(f"[POST-ADAPTER] Fetching post {post_id} from {url}")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)

            logger.debug(f"[POST-ADAPTER] Response status: {resp.status_code}")

            if resp.status_code == 404:
                logger.warning(f"[POST-ADAPTER] Post {post_id} not found")
                raise ValueError(f"Post with ID {post_id} not found")

            resp.raise_for_status()
            result = resp.json()

            logger.info(f"[POST-ADAPTER] Successfully fetched post {post_id}")
            logger.debug(f"[POST-ADAPTER] Post data: {result}")

            return result

    except httpx.TimeoutException as exc:
        logger.error(f"[POST-ADAPTER] Timeout fetching post {post_id}: {exc}")
        raise RuntimeError(f"Timeout while fetching post {post_id}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"[POST-ADAPTER] HTTP error fetching post {post_id}: {exc.response.status_code}")
        raise RuntimeError(f"HTTP {exc.response.status_code} error while fetching post {post_id}")
    except httpx.RequestError as exc:
        logger.error(f"[POST-ADAPTER] Network error fetching post {post_id}: {exc}")
        raise RuntimeError(f"Network error while fetching post {post_id}: {exc}")
    except Exception as exc:
        logger.error(f"[POST-ADAPTER] Unexpected error fetching post {post_id}: {exc}", exc_info=True)
        raise RuntimeError(f"Unexpected error while fetching post {post_id}: {exc}")
