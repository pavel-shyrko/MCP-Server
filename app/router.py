from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from opentelemetry import trace
from app.logger import get_logger as get_app_logger
from app.config import settings, Settings
from app.llm_agent import run_agent, AgentError, LLMConnectionError, LLMResponseError, ToolDispatchError
from app.adapters.jsonplaceholder_post      import handle_request as fetch_post
from app.adapters.jsonplaceholder_comments  import handle_request as fetch_comments

# Get tracer and logger
tracer = trace.get_tracer(__name__)
logger = get_app_logger("router")

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query for the AI agent", json_schema_extra={"example": "Get me post number two"})

class PostRequest(BaseModel):
    post_id: int = Field(..., description="ID of the post to fetch", json_schema_extra={"example": 2})

class CommentsRequest(BaseModel):
    post_id: int = Field(..., description="ID of the post to fetch comments for", json_schema_extra={"example": 2})

def get_settings() -> Settings:
    return settings

def get_router_logger():
    return get_app_logger("router")

router = APIRouter()

@router.post(f"/{settings.post_tool_path}", tags=["Tool API"])
async def post_call(request: PostRequest, settings: Settings = Depends(get_settings), logger=Depends(get_router_logger)):
    """
    Tool #1: Fetch a post from JSONPlaceholder by ID.

    Example request:
    ```json
    {"post_id": 2}
    ```
    """
    with tracer.start_as_current_span("router.post_call") as span:
        try:
            data = request.model_dump()  # was request.dict()
            span.set_attribute("tool.name", "post_call")
            span.set_attribute("post.id", data.get("post_id"))
            logger.info(f"Fetching post with args={data!r}")

            result = await fetch_post(data)
            span.set_attribute("request.success", True)
            logger.info(f"Successfully fetched post {data.get('post_id')}")
            return result

        except Exception as exc:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR))
            span.record_exception(exc)
            logger.error(f"Error fetching post: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to fetch post: {str(exc)}")

@router.post(f"/{settings.comments_tool_path}", tags=["Tool API"])
async def comments_call(request: CommentsRequest, settings: Settings = Depends(get_settings), logger=Depends(get_router_logger)):
    """
    Tool #2: Fetch comments for a given post ID.

    Example request:
    ```json
    {"post_id": 2}
    ```
    """
    with tracer.start_as_current_span("router.comments_call") as span:
        try:
            data = request.model_dump()  # was request.dict()
            span.set_attribute("tool.name", "comments_call")
            span.set_attribute("post.id", data.get("post_id"))
            logger.info(f"Fetching comments with args={data!r}")

            result = await fetch_comments(data)
            span.set_attribute("request.success", True)
            logger.info(f"Successfully fetched comments for post {data.get('post_id')}")
            return result

        except Exception as exc:
            span.set_status(trace.status.Status(trace.status.StatusCode.ERROR))
            span.record_exception(exc)
            logger.error(f"Error fetching comments: {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to fetch comments: {str(exc)}")

@router.post("/ask", tags=["Agent"])
async def ask_llm(request: QueryRequest, logger=Depends(get_router_logger)):
    """
    Agent endpoint: Ask the AI agent to perform tasks using available tools.

    The agent can:
    1) Fetch posts by ID using natural language
    2) Fetch comments for posts
    3) Chain multiple operations based on context

    Example requests:
    ```json
    {"query": "Get me post number two"}
    {"query": "Now show me all comments for that post"}
    {"query": "покажи мне публикацию номер два"}
    ```

    The agent will:
    1) Send your query + system prompt to Ollama (mistral model)
    2) Parse the response to determine which tool to call
    3) Execute the appropriate tool with the correct parameters
    4) Return the results
    """
    with tracer.start_as_current_span("router.ask_llm") as span:
        query = request.query
        span.set_attribute("user.query", query)
        logger.info(f"Processing query: {query!r}")

        try:
            result = await run_agent(query)
            span.set_attribute("request.success", True)
            logger.info(f"Query processed successfully")
            return {"result": result, "status": "success"}

        except LLMConnectionError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "LLM connection error"))
            span.set_attribute("error.type", "llm_connection_error")
            logger.error(f"LLM connection error: {exc}")
            return {
                "error": "LLM service unavailable",
                "details": str(exc),
                "error_type": "llm_connection_error",
                "status": "error"
            }

        except LLMResponseError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "LLM response error"))
            span.set_attribute("error.type", "llm_response_error")
            logger.error(f"LLM response error: {exc}")
            return {
                "error": "Invalid response from LLM",
                "details": str(exc),
                "error_type": "llm_response_error",
                "status": "error"
            }

        except ToolDispatchError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Tool dispatch error"))
            span.set_attribute("error.type", "tool_dispatch_error")
            logger.error(f"Tool dispatch error: {exc}")
            return {
                "error": "Tool execution failed",
                "details": str(exc),
                "error_type": "tool_dispatch_error",
                "status": "error"
            }

        except AgentError as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Agent error"))
            span.set_attribute("error.type", "agent_error")
            logger.error(f"Agent error: {exc}")
            return {
                "error": "Agent execution failed",
                "details": str(exc),
                "error_type": "agent_error",
                "status": "error"
            }

        except Exception as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Internal error"))
            span.set_attribute("error.type", "internal_error")
            logger.error(f"Unexpected error: {exc}", exc_info=True)
            return {
                "error": "Internal server error",
                "details": "An unexpected error occurred while processing your request",
                "error_type": "internal_error",
                "status": "error"
            }
