import json
import httpx
from app.logger import logger
from app.config import settings

async def run_agent(query: str) -> dict:
    """
    1) Send system+user prompt to Ollama’s /api/chat.
    2) Read and stitch the newline-delimited JSON chunks into one string.
    3) Parse that string as {"tool": "...", "args": {...}}.
    4) Normalize the tool name (underscore→hyphen) and call the matching /<tool>-call.
    5) Return the adapter’s JSON response.
    """
    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": settings.system_prompt},
            {"role": "user",   "content": query},
        ],
    }

    # 1) call Ollama
    llm_base = str(settings.llm_base_url).rstrip("/")
    chat_url = f"{llm_base}/api/chat"
    logger.info(f"[AGENT] POST to Ollama at {chat_url} payload={payload!r}")

    async with httpx.AsyncClient() as cli:
        resp = await cli.post(chat_url, json=payload, timeout=30.0)
        resp.raise_for_status()
        raw = resp.text

    # 2) stitch streaming chunks
    contents = []
    for line in raw.splitlines():
        try:
            chunk = json.loads(line)
            part  = chunk.get("message", {}).get("content", "")
            if part:
                contents.append(part)
        except json.JSONDecodeError:
            logger.warning(f"[AGENT] Skipping unparseable line: {line!r}")

    assistant_json_str = "".join(contents).strip()
    logger.info(f"[AGENT] Full assistant JSON string: {assistant_json_str!r}")

    # 3) parse tool + args
    try:
        js   = json.loads(assistant_json_str)
        tool = js["tool"]
        args = js["args"]
    except Exception as exc:
        raise ValueError(f"Failed parsing tool JSON: {exc}: {assistant_json_str}")

    # 4) normalize tool name (underscore → hyphen)
    tool_path = tool.replace("_", "-")
    local_base = str(settings.local_api_base).rstrip("/")
    url = f"{local_base}/{tool_path}"
    logger.info(f"[AGENT] Dispatching to {url} with args={args!r}")

    # 5) call the adapter
    async with httpx.AsyncClient() as cli:
        tool_resp = await cli.post(url, json=args, timeout=30.0)
        tool_resp.raise_for_status()
        return tool_resp.json()
