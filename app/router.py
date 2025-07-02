from fastapi import APIRouter, Request
from app.adapters import booking
from app.auth import get_user_token
from app.logger import logger
from app.llm_agent import run_agent

router = APIRouter()

@router.get("/health", tags=["Service"])
async def healthcheck():
    """Healthcheck endpoint for container monitoring"""
    return {"status": "ok"}


@router.post("/tool-call", tags=["Tool API"])
async def tool_call(request: Request):
    """
    Executes a call to an internal adapter (e.g., booking).
    Expects a JSON payload and user token.
    """
    data = await request.json()
    logger.info(f"Tool-call input: {data}")
    user_token = get_user_token(request)
    response = await booking.handle_request(data, user_token)
    logger.info(f"Tool-call response: {response}")
    return response


@router.post("/ask", tags=["LangChain Agent"])
async def ask_llm(request: Request):
    """
    Sends a natural language query to LLM (via Ollama).
    The agent decides which tool to call.
    """
    data = await request.json()
    query = data.get("query")
    logger.info(f"LLM query: {query}")
    result = run_agent(query)
    logger.info(f"LLM response: {result}")
    return {"response": result}
