import json
import httpx
from typing import Dict, Any
from opentelemetry import trace
from app.logger import get_logger
from app.config import settings

# Get tracer and logger
tracer = trace.get_tracer(__name__)
logger = get_logger("llm-agent")

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
    with tracer.start_as_current_span("agent.run_agent") as span:
        span.set_attribute("agent.query", query)
        logger.info(f"Starting agent execution for query: {query!r}")

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

        with tracer.start_as_current_span("agent.ollama_request") as ollama_span:
            ollama_span.set_attribute("http.url", chat_url)
            ollama_span.set_attribute("llm.model", "mistral")
            logger.info(f"Sending request to Ollama at {chat_url}")
            logger.debug(f"Payload: {payload}")

            try:
                async with httpx.AsyncClient() as cli:
                    resp = await cli.post(chat_url, json=payload, timeout=30.0)
                    resp.raise_for_status()
                    raw = resp.text
                    ollama_span.set_attribute("http.status_code", resp.status_code)
                    ollama_span.set_attribute("http.response_size", len(raw))
                    logger.debug(f"Raw LLM response length: {len(raw)} chars")
            except httpx.TimeoutException as exc:
                ollama_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Timeout connecting to Ollama: {exc}")
                raise LLMConnectionError(f"Timeout connecting to LLM service at {chat_url}")
            except httpx.HTTPStatusError as exc:
                ollama_span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {exc.response.status_code}"))
                logger.error(f"HTTP error from Ollama: {exc.response.status_code} - {exc.response.text}")
                raise LLMConnectionError(f"HTTP {exc.response.status_code} error from LLM service")
            except httpx.RequestError as exc:
                ollama_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Network error connecting to Ollama: {exc}")
                raise LLMConnectionError(f"Network error connecting to LLM service: {exc}")
            except Exception as exc:
                ollama_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Unexpected error calling Ollama: {exc}", exc_info=True)
                raise LLMConnectionError(f"Unexpected error calling LLM service: {exc}")

        # 2) stitch streaming chunks with improved error handling
        with tracer.start_as_current_span("agent.process_response") as process_span:
            contents = []
            valid_chunks = 0
            invalid_chunks = 0

            logger.debug(f"Processing {len(raw.splitlines())} response lines")

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
                    logger.warning(f"Line {line_num}: Skipping unparseable JSON: {exc} - {line!r}")

            process_span.set_attribute("chunks.valid", valid_chunks)
            process_span.set_attribute("chunks.invalid", invalid_chunks)
            logger.info(f"Processed {valid_chunks} valid chunks, {invalid_chunks} invalid chunks")

            assistant_json_str = "".join(contents).strip()
            logger.info(f"Assembled response: {assistant_json_str!r}")

            if not assistant_json_str:
                process_span.set_status(trace.Status(trace.StatusCode.ERROR, "Empty LLM response"))
                logger.error("Empty response from LLM")
                raise LLMResponseError("LLM returned empty response")

        # 3) parse tool + args with detailed error handling
        with tracer.start_as_current_span("agent.parse_tool") as parse_span:
            try:
                js = json.loads(assistant_json_str)
                logger.debug(f"Parsed JSON structure: {js}")

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

                parse_span.set_attribute("tool.name", tool)
                parse_span.set_attribute("tool.args", str(args))
                logger.info(f"Extracted tool: {tool!r}, args: {args!r}")

            except json.JSONDecodeError as exc:
                parse_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"JSON parsing failed: {exc}")
                raise LLMResponseError(f"Invalid JSON in LLM response: {exc}")
            except (KeyError, ValueError) as exc:
                parse_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Invalid response structure: {exc}")
                raise LLMResponseError(f"Invalid response structure: {exc}")
            except Exception as exc:
                parse_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Unexpected error parsing response: {exc}", exc_info=True)
                raise LLMResponseError(f"Unexpected error parsing LLM response: {exc}")

        # 4) normalize tool name and prepare URL
        tool_path = tool.replace("_", "-")
        local_base = str(settings.local_api_base).rstrip("/")
        url = f"{local_base}/{tool_path}"
        logger.info(f"Normalized tool path: {tool!r} -> {tool_path!r}")
        logger.info(f"Dispatching to: {url}")

        # 5) call the adapter with comprehensive error handling
        with tracer.start_as_current_span("agent.dispatch_tool") as dispatch_span:
            dispatch_span.set_attribute("tool.name", tool)
            dispatch_span.set_attribute("tool.path", tool_path)
            dispatch_span.set_attribute("http.url", url)

            try:
                async with httpx.AsyncClient() as cli:
                    logger.debug(f"Sending tool request with args: {args}")
                    tool_resp = await cli.post(url, json=args, timeout=30.0)

                    dispatch_span.set_attribute("http.status_code", tool_resp.status_code)
                    logger.info(f"Tool response status: {tool_resp.status_code}")

                    if tool_resp.status_code == 404:
                        dispatch_span.set_status(trace.Status(trace.StatusCode.ERROR, "Tool not found"))
                        logger.error(f"Tool not found: {tool_path}")
                        raise ToolDispatchError(f"Tool '{tool}' not found (path: {tool_path})")

                    tool_resp.raise_for_status()
                    result = tool_resp.json()

                    dispatch_span.set_attribute("tool.result_type", type(result).__name__)
                    span.set_attribute("agent.success", True)
                    logger.info(f"Tool execution successful, result type: {type(result).__name__}")
                    logger.debug(f"Tool result: {result}")

                    return result

            except httpx.TimeoutException as exc:
                dispatch_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Timeout calling tool {tool_path}: {exc}")
                raise ToolDispatchError(f"Timeout calling tool '{tool}'")
            except httpx.HTTPStatusError as exc:
                dispatch_span.set_status(trace.Status(trace.StatusCode.ERROR, f"HTTP {exc.response.status_code}"))
                logger.error(f"HTTP error from tool {tool_path}: {exc.response.status_code}")
                try:
                    error_detail = exc.response.json()
                    logger.error(f"Tool error details: {error_detail}")
                except:
                    logger.error(f"Tool error response: {exc.response.text}")
                raise ToolDispatchError(f"Tool '{tool}' returned HTTP {exc.response.status_code}")
            except httpx.RequestError as exc:
                dispatch_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Network error calling tool {tool_path}: {exc}")
                raise ToolDispatchError(f"Network error calling tool '{tool}': {exc}")
            except json.JSONDecodeError as exc:
                dispatch_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Invalid JSON response from tool {tool_path}: {exc}")
                raise ToolDispatchError(f"Tool '{tool}' returned invalid JSON")
            except Exception as exc:
                dispatch_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
                logger.error(f"Unexpected error calling tool {tool_path}: {exc}", exc_info=True)
                raise ToolDispatchError(f"Unexpected error calling tool '{tool}': {exc}")
