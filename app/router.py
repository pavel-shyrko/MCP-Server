from fastapi import APIRouter, Request
from app.logger import logger
from app.config import settings
from app.llm_agent import run_agent
from app.adapters.jsonplaceholder_post      import handle_request as fetch_post
from app.adapters.jsonplaceholder_comments  import handle_request as fetch_comments

router = APIRouter()

@router.post(f"/{settings.post_tool_path}", tags=["Tool API"])
async def post_call(request: Request):
    """
    Tool #1: Fetch a post from JSONPlaceholder by ID.
    """
    data = await request.json()
    logger.info(f"[POST-CALL] args={data!r}")
    return await fetch_post(data)

@router.post(f"/{settings.comments_tool_path}", tags=["Tool API"])
async def comments_call(request: Request):
    """
    Tool #2: Fetch comments for a given post ID.
    """
    data = await request.json()
    logger.info(f"[COMMENTS-CALL] args={data!r}")
    return await fetch_comments(data)

@router.post("/ask", tags=["Agent"])
async def ask_llm(request: Request):
    """
    Agent endpoint:
    1) Send user query + system prompt to Ollama.
    2) Parse JSON: {"tool": "...", "args": {...}}.
    3) Dispatch to the matching tool endpoint.
    """
    data  = await request.json()
    query = data.get("query", "")
    logger.info(f"[ASK] query={query!r}")
    try:
        result = await run_agent(query)
        return {"result": result}
    except Exception as exc:
        logger.error(f"[ASK] error: {exc}", exc_info=True)
        return {"error": str(exc)}
