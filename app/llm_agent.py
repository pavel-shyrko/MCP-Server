from langchain_ollama import ChatOllama
from langchain.agents import Tool
from langgraph.prebuilt import create_react_agent
import json
from app.logger import logger

# ——— Tool definition ———
def booking_tool_func(input_data: str):
    data = json.loads(input_data)
    return f"Simulated booking API call with: {data}"

booking_tool = Tool(
    name="booking_tool",
    func=booking_tool_func,
    description="Used to book desks. Input is JSON with fields: action, date."
)

# ——— LLM client ———
llm = ChatOllama(model="mistral", base_url="http://host.docker.internal:11434")

# ——— Agent graph ———
graph = create_react_agent(
    model=llm,
    tools=[booking_tool]
)

# ——— Unified interface ———
def run_agent(query: str) -> str:
    """
    Invoke the LangGraph agent and extract the textual output.
    1) Если LLM возвращает plain string — сразу его.
    2) Если dict с ключом 'messages' — собираем content.
    3) Если messages есть, но все content пустые — сообщаем об этом.
    4) Ищем ключи 'output', 'result', 'response', 'text'.
    5) Иначе — human-friendly fallback.
    """
    try:
        raw = graph.invoke({"input": query})
        logger.info(f"[LLM_AGENT] raw graph response: {raw!r}")

        # 1) Plain string
        if isinstance(raw, str):
            return raw

        # 2) Dict with messages
        if isinstance(raw, dict) and "messages" in raw:
            msgs = raw["messages"]
            # Collect non-empty contents
            parts = [getattr(m, "content", "") for m in msgs]
            nonempty = [p for p in parts if p.strip()]
            if nonempty:
                return "\n".join(nonempty)
            # 3) messages present but empty
            logger.warning("[LLM_AGENT] messages present but all content empty")
            return "LLM returned no content."

        # 4) Other common keys
        if isinstance(raw, dict):
            for key in ("output", "result", "response", "text"):
                if key in raw and raw[key] not in (None, ""):
                    return raw[key]

        # 5) Fallback
        return f"Unexpected response format: {raw}"

    except Exception as exc:
        logger.error("[LLM_AGENT] error invoking graph", exc_info=True)
        return f"Error during agent execution: {exc}"
