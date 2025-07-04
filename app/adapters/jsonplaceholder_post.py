import httpx
from opentelemetry import trace
from app.config import settings
from app.logger import get_logger

# Get tracer and logger
tracer = trace.get_tracer(__name__)
logger = get_logger("post-adapter")

async def handle_request(data: dict) -> dict:
    """
    Fetch a post by ID from JSONPlaceholder.
    Expects: {"post_id": <int>}
    """
    with tracer.start_as_current_span("adapter.fetch_post") as span:
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

        url = f"{settings.jsonplaceholder_base_url}/posts/{post_id}"
        span.set_attribute("http.url", url)
        logger.info(f"Fetching post {post_id} from {url}")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)

                span.set_attribute("http.status_code", resp.status_code)
                logger.debug(f"Response status: {resp.status_code}")

                if resp.status_code == 404:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Post not found"))
                    logger.warning(f"Post {post_id} not found")
                    raise ValueError(f"Post with ID {post_id} not found")

                resp.raise_for_status()
                result = resp.json()

                span.set_attribute("post.title", result.get("title", "")[:100])  # Truncate for span
                span.set_attribute("post.user_id", result.get("userId"))
                logger.info(f"Successfully fetched post {post_id}")
                logger.debug(f"Post data: {result}")

                return result

        except httpx.TimeoutException as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error(f"Timeout fetching post {post_id}: {exc}")
            raise RuntimeError(f"Timeout while fetching post {post_id}")
        except httpx.HTTPStatusError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {exc.response.status_code}"))
            logger.error(f"HTTP error fetching post {post_id}: {exc.response.status_code}")
            raise RuntimeError(f"HTTP {exc.response.status_code} error while fetching post {post_id}")
        except httpx.RequestError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error(f"Network error fetching post {post_id}: {exc}")
            raise RuntimeError(f"Network error while fetching post {post_id}: {exc}")
        except Exception as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            logger.error(f"Unexpected error fetching post {post_id}: {exc}", exc_info=True)
            raise RuntimeError(f"Unexpected error while fetching post {post_id}: {exc}")
