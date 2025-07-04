import httpx
from app.config import settings
from app.logger import logger

async def handle_request(data: dict) -> list:
    """
    Fetch comments for a given post ID.
    Expects: {"post_id": <int>}
    """
    post_id = data.get("post_id")

    if post_id is None:
        logger.error("[COMMENTS-ADAPTER] Missing post_id in request data")
        raise ValueError("post_id is required")

    if not isinstance(post_id, int) or post_id <= 0:
        logger.error(f"[COMMENTS-ADAPTER] Invalid post_id: {post_id}")
        raise ValueError(f"post_id must be a positive integer, got: {post_id}")

    url = f"{settings.jsonplaceholder_base_url}/comments"
    params = {"postId": post_id}
    logger.info(f"[COMMENTS-ADAPTER] Fetching comments for post {post_id} from {url}")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=5.0)

            logger.debug(f"[COMMENTS-ADAPTER] Response status: {resp.status_code}")
            resp.raise_for_status()

            result = resp.json()

            if not isinstance(result, list):
                logger.warning(f"[COMMENTS-ADAPTER] Unexpected response type: {type(result)}")
                raise RuntimeError(f"Expected list of comments, got {type(result).__name__}")

            logger.info(f"[COMMENTS-ADAPTER] Successfully fetched {len(result)} comments for post {post_id}")
            logger.debug(f"[COMMENTS-ADAPTER] Comments data: {result}")

            return result

    except httpx.TimeoutException as exc:
        logger.error(f"[COMMENTS-ADAPTER] Timeout fetching comments for post {post_id}: {exc}")
        raise RuntimeError(f"Timeout while fetching comments for post {post_id}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"[COMMENTS-ADAPTER] HTTP error fetching comments for post {post_id}: {exc.response.status_code}")
        raise RuntimeError(f"HTTP {exc.response.status_code} error while fetching comments for post {post_id}")
    except httpx.RequestError as exc:
        logger.error(f"[COMMENTS-ADAPTER] Network error fetching comments for post {post_id}: {exc}")
        raise RuntimeError(f"Network error while fetching comments for post {post_id}: {exc}")
    except Exception as exc:
        logger.error(f"[COMMENTS-ADAPTER] Unexpected error fetching comments for post {post_id}: {exc}", exc_info=True)
        raise RuntimeError(f"Unexpected error while fetching comments for post {post_id}: {exc}")
