import json
import httpx
from typing import Dict, Any
from app.logger import logger
from app.config import settings

class AgentError(Exception):
    """Base exception for agent-related errors"""
    pass

class LLMConnectionError(AgentError):
    """Error connecting to LLM service"""
    pass

class LLMResponseError(AgentError):
    """Error parsing LLM response"""
    pass

class ToolDispatchError(AgentError):
    """Error dispatching to tool"""
    pass

async def run_agent(query: str) -> Dict[str, Any]:
    """
    1) Send system+user prompt to Ollama's /api/chat.
    2) Read and stitch the newline-delimited JSON chunks into one string.
    3) Parse that string as {"tool": "...", "args": {...}}.
    4) Normalize the tool name (underscore→hyphen) and call the matching /<tool>-call.
    5) Return the adapter's JSON response.
    """
    logger.info(f"[AGENT] Starting agent execution for query: {query!r}")

    payload = {
        "model": "mistral",
        "messages": [
            {"role": "system", "content": settings.system_prompt},
            {"role": "user",   "content": query},
        ],
    }

    # 1) call Ollama with error handling
    llm_base = str(settings.llm_base_url).rstrip("/")
    chat_url = f"{llm_base}/api/chat"
    logger.info(f"[AGENT] Sending request to Ollama at {chat_url}")
    logger.debug(f"[AGENT] Payload: {payload}")

    try:
        async with httpx.AsyncClient() as cli:
            resp = await cli.post(chat_url, json=payload, timeout=30.0)
            resp.raise_for_status()
            raw = resp.text
            logger.debug(f"[AGENT] Raw LLM response length: {len(raw)} chars")
    except httpx.TimeoutException as exc:
        logger.error(f"[AGENT] Timeout connecting to Ollama: {exc}")
        raise LLMConnectionError(f"Timeout connecting to LLM service at {chat_url}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"[AGENT] HTTP error from Ollama: {exc.response.status_code} - {exc.response.text}")
        raise LLMConnectionError(f"HTTP {exc.response.status_code} error from LLM service")
    except httpx.RequestError as exc:
        logger.error(f"[AGENT] Network error connecting to Ollama: {exc}")
        raise LLMConnectionError(f"Network error connecting to LLM service: {exc}")
    except Exception as exc:
        logger.error(f"[AGENT] Unexpected error calling Ollama: {exc}", exc_info=True)
        raise LLMConnectionError(f"Unexpected error calling LLM service: {exc}")

    # 2) stitch streaming chunks with improved error handling
    contents = []
    valid_chunks = 0
    invalid_chunks = 0

    logger.debug(f"[AGENT] Processing {len(raw.splitlines())} response lines")

    for line_num, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue

        try:
            chunk = json.loads(line)
            part = chunk.get("message", {}).get("content", "")
            if part:
                contents.append(part)
                valid_chunks += 1
        except json.JSONDecodeError as exc:
            invalid_chunks += 1
            logger.warning(f"[AGENT] Line {line_num}: Skipping unparseable JSON: {exc} - {line!r}")

    logger.info(f"[AGENT] Processed {valid_chunks} valid chunks, {invalid_chunks} invalid chunks")

    assistant_json_str = "".join(contents).strip()
    logger.info(f"[AGENT] Assembled response: {assistant_json_str!r}")

    if not assistant_json_str:
        logger.error("[AGENT] Empty response from LLM")
        raise LLMResponseError("LLM returned empty response")

    # 3) parse tool + args with detailed error handling
    try:
        js = json.loads(assistant_json_str)
        logger.debug(f"[AGENT] Parsed JSON structure: {js}")

        if not isinstance(js, dict):
            raise ValueError(f"Expected dict, got {type(js).__name__}")

        if "tool" not in js:
            raise ValueError("Missing 'tool' key in response")
        if "args" not in js:
            raise ValueError("Missing 'args' key in response")

        tool = js["tool"]
        args = js["args"]

        if not isinstance(tool, str):
            raise ValueError(f"Tool must be string, got {type(tool).__name__}")
        if not isinstance(args, dict):
            raise ValueError(f"Args must be dict, got {type(args).__name__}")

        logger.info(f"[AGENT] Extracted tool: {tool!r}, args: {args!r}")

    except json.JSONDecodeError as exc:
        logger.error(f"[AGENT] JSON parsing failed: {exc}")
        raise LLMResponseError(f"Invalid JSON in LLM response: {exc}")
    except (KeyError, ValueError) as exc:
        logger.error(f"[AGENT] Invalid response structure: {exc}")
        raise LLMResponseError(f"Invalid response structure: {exc}")
    except Exception as exc:
        logger.error(f"[AGENT] Unexpected error parsing response: {exc}", exc_info=True)
        raise LLMResponseError(f"Unexpected error parsing LLM response: {exc}")

    # 4) normalize tool name and prepare URL
    tool_path = tool.replace("_", "-")
    local_base = str(settings.local_api_base).rstrip("/")
    url = f"{local_base}/{tool_path}"
    logger.info(f"[AGENT] Normalized tool path: {tool!r} -> {tool_path!r}")
    logger.info(f"[AGENT] Dispatching to: {url}")

    # 5) call the adapter with comprehensive error handling
    try:
        async with httpx.AsyncClient() as cli:
            logger.debug(f"[AGENT] Sending tool request with args: {args}")
            tool_resp = await cli.post(url, json=args, timeout=30.0)

            logger.info(f"[AGENT] Tool response status: {tool_resp.status_code}")

            if tool_resp.status_code == 404:
                logger.error(f"[AGENT] Tool not found: {tool_path}")
                raise ToolDispatchError(f"Tool '{tool}' not found (path: {tool_path})")

            tool_resp.raise_for_status()
            result = tool_resp.json()

            logger.info(f"[AGENT] Tool execution successful, result type: {type(result).__name__}")
            logger.debug(f"[AGENT] Tool result: {result}")

            return result

    except httpx.TimeoutException as exc:
        logger.error(f"[AGENT] Timeout calling tool {tool_path}: {exc}")
        raise ToolDispatchError(f"Timeout calling tool '{tool}'")
    except httpx.HTTPStatusError as exc:
        logger.error(f"[AGENT] HTTP error from tool {tool_path}: {exc.response.status_code}")
        try:
            error_detail = exc.response.json()
            logger.error(f"[AGENT] Tool error details: {error_detail}")
        except:
            logger.error(f"[AGENT] Tool error response: {exc.response.text}")
        raise ToolDispatchError(f"Tool '{tool}' returned HTTP {exc.response.status_code}")
    except httpx.RequestError as exc:
        logger.error(f"[AGENT] Network error calling tool {tool_path}: {exc}")
        raise ToolDispatchError(f"Network error calling tool '{tool}': {exc}")
    except json.JSONDecodeError as exc:
        logger.error(f"[AGENT] Invalid JSON response from tool {tool_path}: {exc}")
        raise ToolDispatchError(f"Tool '{tool}' returned invalid JSON")
    except Exception as exc:
        logger.error(f"[AGENT] Unexpected error calling tool {tool_path}: {exc}", exc_info=True)
        raise ToolDispatchError(f"Unexpected error calling tool '{tool}': {exc}")
