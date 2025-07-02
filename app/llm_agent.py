from langchain_ollama import ChatOllama
from langchain.agents import Tool
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
import json
from app.logger import logger

# Simulated tool logic
def booking_tool_func(input_data: str):
    data = json.loads(input_data)
    return f"Simulated booking API call with: {data}"

# Define the tool
booking_tool = Tool(
    name="booking_tool",
    func=booking_tool_func,
    description="Used to book desks. Input is JSON with fields: action, date."
)

# Initialize the LLM client (Ollama)
llm = ChatOllama(model="mistral", base_url="http://host.docker.internal:11434")

# Build the agent graph (ReAct)
graph = create_react_agent(
    model=llm,
    tools=[booking_tool]
)

def run_agent(query: str) -> str:
    """
    Invoke the LangGraph agent and extract the textual output.
    Handles:
      - Plain string responses
      - Dicts with 'messages': [AIMessage, ...]
      - Known keys: 'output', 'result', 'response', 'text'
    Falls back to str(raw) on anything else.
    """
    try:
        raw = graph.invoke({"input": query})
        logger.info(f"[LLM_AGENT] raw graph response: {raw!r}")

        # 1) If it's a plain string, return directly
        if isinstance(raw, str):
            return raw

        # 2) If dict with 'messages' (list of AIMessage)
        if isinstance(raw, dict) and 'messages' in raw and isinstance(raw['messages'], list):
            parts = []
            for msg in raw['messages']:
                # AIMessage has .content
                content = getattr(msg, "content", None)
                if content:
                    parts.append(content)
            joined = "\n".join(parts).strip()
            if joined:
                return joined

        # 3) Check other common keys
        if isinstance(raw, dict):
            for key in ("output", "result", "response", "text"):
                if key in raw:
                    return raw[key]

        # 4) Fallback: just stringify
        return str(raw)

    except Exception as exc:
        logger.error("[LLM_AGENT] error invoking graph", exc_info=True)
        return f"Error during agent execution: {exc}"
