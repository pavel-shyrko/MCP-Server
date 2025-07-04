import httpx
from opentelemetry import trace
from app.config import settings
from app.logger import get_logger

# Get tracer and logger
tracer = trace.get_tracer(__name__)
logger = get_logger("comments-adapter")

async def handle_request(data: dict) -> list:
    """
    Fetch comments for a given post ID.
    Expects: {"post_id": <int>}
    """
    with tracer.start_as_current_span("adapter.fetch_comments") as span:
        post_id = data.get("post_id")
        span.set_attribute("post.id", post_id)

        if post_id is None:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing post_id"))
            logger.error("Missing post_id in request data")
            raise ValueError("post_id is required")

        if not isinstance(post_id, int) or post_id <= 0:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Invalid post_id: {post_id}"))
            logger.error(f"Invalid post_id: {post_id}")
            raise ValueError(f"post_id must be a positive integer, got: {post_id}")

        url = f"{settings.jsonplaceholder_base_url}/comments"
        params = {"postId": post_id}
        span.set_attribute("http.url", url)
        span.set_attribute("http.params", str(params))
        logger.info(f"Fetching comments for post {post_id} from {url}")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=5.0)

                span.set_attribute("http.status_code", resp.status_code)
                logger.debug(f"Response status: {resp.status_code}")
                resp.raise_for_status()

                result = resp.json()

                if not isinstance(result, list):
                    span.set_status(trace.Status(trace.StatusCode.ERROR, f"Unexpected response type: {type(result)}"))
                    logger.warning(f"Unexpected response type: {type(result)}")
                    raise RuntimeError(f"Expected list of comments, got {type(result).__name__}")

                span.set_attribute("comments.count", len(result))
                logger.info(f"Successfully fetched {len(result)} comments for post {post_id}")
                logger.debug(f"Comments data: {result}")

                return result

        except httpx.TimeoutException as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error(f"Timeout fetching comments for post {post_id}: {exc}")
            raise RuntimeError(f"Timeout while fetching comments for post {post_id}")
        except httpx.HTTPStatusError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {exc.response.status_code}"))
            logger.error(f"HTTP error fetching comments for post {post_id}: {exc.response.status_code}")
            raise RuntimeError(f"HTTP {exc.response.status_code} error while fetching comments for post {post_id}")
        except httpx.RequestError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error(f"Network error fetching comments for post {post_id}: {exc}")
            raise RuntimeError(f"Network error while fetching comments for post {post_id}: {exc}")
        except Exception as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error(f"Unexpected error fetching comments for post {post_id}: {exc}", exc_info=True)
            raise RuntimeError(f"Unexpected error while fetching comments for post {post_id}: {exc}")
