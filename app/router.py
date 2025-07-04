from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from app.logger import logger
from app.config import settings, Settings
from app.llm_agent import run_agent, AgentError, LLMConnectionError, LLMResponseError, ToolDispatchError
from app.adapters.jsonplaceholder_post      import handle_request as fetch_post
from app.adapters.jsonplaceholder_comments  import handle_request as fetch_comments

class QueryRequest(BaseModel):
    query: str = Field(..., example="Get me post number two", description="Natural language query for the AI agent")

class PostRequest(BaseModel):
    post_id: int = Field(..., example=2, description="ID of the post to fetch")

class CommentsRequest(BaseModel):
    post_id: int = Field(..., example=2, description="ID of the post to fetch comments for")

def get_settings() -> Settings:
    return settings

def get_logger():
    return logger

router = APIRouter()

@router.post(f"/{settings.post_tool_path}", tags=["Tool API"])
async def post_call(request: PostRequest, settings: Settings = Depends(get_settings), logger=Depends(get_logger)):
    """
    Tool #1: Fetch a post from JSONPlaceholder by ID.

    Example request:
    ```json
    {"post_id": 2}
    ```
    """
    data = request.dict()
    logger.info(f"[POST-CALL] args={data!r}")
    return await fetch_post(data)

@router.post(f"/{settings.comments_tool_path}", tags=["Tool API"])
async def comments_call(request: CommentsRequest, settings: Settings = Depends(get_settings), logger=Depends(get_logger)):
    """
    Tool #2: Fetch comments for a given post ID.

    Example request:
    ```json
    {"post_id": 2}
    ```
    """
    data = request.dict()
    logger.info(f"[COMMENTS-CALL] args={data!r}")
    return await fetch_comments(data)

@router.post("/ask", tags=["Agent"])
async def ask_llm(request: QueryRequest, logger=Depends(get_logger)):
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
    query = request.query
    logger.info(f"[ASK] Processing query: {query!r}")

    try:
        result = await run_agent(query)
        logger.info(f"[ASK] Query processed successfully")
        return {"result": result, "status": "success"}

    except LLMConnectionError as exc:
        logger.error(f"[ASK] LLM connection error: {exc}")
        return {
            "error": "LLM service unavailable",
            "details": str(exc),
            "error_type": "llm_connection_error",
            "status": "error"
        }

    except LLMResponseError as exc:
        logger.error(f"[ASK] LLM response error: {exc}")
        return {
            "error": "Invalid response from LLM",
            "details": str(exc),
            "error_type": "llm_response_error",
            "status": "error"
        }

    except ToolDispatchError as exc:
        logger.error(f"[ASK] Tool dispatch error: {exc}")
        return {
            "error": "Tool execution failed",
            "details": str(exc),
            "error_type": "tool_dispatch_error",
            "status": "error"
        }

    except AgentError as exc:
        logger.error(f"[ASK] Agent error: {exc}")
        return {
            "error": "Agent execution failed",
            "details": str(exc),
            "error_type": "agent_error",
            "status": "error"
        }

    except Exception as exc:
        logger.error(f"[ASK] Unexpected error: {exc}", exc_info=True)
        return {
            "error": "Internal server error",
            "details": "An unexpected error occurred while processing your request",
            "error_type": "internal_error",
            "status": "error"
        }
