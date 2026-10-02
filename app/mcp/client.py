"""In-process and protocol-compliant MCP Client for discovering and invoking tools."""

import time
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.core.metrics import (
    TOOL_CALLS_TOTAL,
    TOOL_ERRORS_TOTAL,
    TOOL_EXECUTION_DURATION_SECONDS,
)
from app.mcp.schemas import MCPToolDefinition, ToolExecutionResult
from mcp_server.schemas import is_write_tool
from mcp_server.server import mcp_server


class MCPClient:
    """Discovers MCP tools dynamically and executes them with observability."""

    def __init__(self, server=None):
        self.server = server or mcp_server
        self._cached_tools: Optional[List[MCPToolDefinition]] = None

    async def discover_tools(self, force_refresh: bool = False) -> List[MCPToolDefinition]:
        """Query MCP server to discover available tools and their input schemas."""
        if self._cached_tools is not None and not force_refresh:
            return self._cached_tools

        raw_tools = await self.server.list_tools()
        definitions: List[MCPToolDefinition] = []

        for t in raw_tools:
            # Extract parameters schema
            schema = {}
            if hasattr(t, "inputSchema") and t.inputSchema:
                schema = t.inputSchema
            elif hasattr(t, "parameters") and t.parameters:
                schema = t.parameters

            write_flag = is_write_tool(t.name)
            definitions.append(
                MCPToolDefinition(
                    name=t.name,
                    description=t.description or "",
                    input_schema=schema,
                    is_write=write_flag,
                    requires_confirmation=write_flag,
                )
            )

        self._cached_tools = definitions
        logger.info(
            f"Discovered {len(definitions)} MCP tools from server",
            extra={"event": "mcp_discovery", "tool_count": len(definitions)},
        )
        return definitions

    async def get_tool_definitions_for_llm(self) -> List[Dict[str, Any]]:
        """Format discovered MCP tools into standard LLM function calling declarations."""
        tools = await self.discover_tools()
        llm_tools = []
        for t in tools:
            llm_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
            )
        return llm_tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """Execute tool on MCP server with timing, metrics, and structured logging."""
        start_time = time.perf_counter()
        write_flag = is_write_tool(tool_name)

        logger.info(
            f"Executing MCP tool '{tool_name}'",
            extra={
                "event": "tool_execution_start",
                "tool": tool_name,
                "extra_data": {"arguments": arguments, "is_write": write_flag},
            },
        )

        try:
            raw_result = await self.server.call_tool(tool_name, arguments)
            duration_ms = (time.perf_counter() - start_time) * 1000
            duration_sec = duration_ms / 1000.0

            # Record Prometheus metrics
            TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="success").inc()
            TOOL_EXECUTION_DURATION_SECONDS.labels(tool_name=tool_name).observe(duration_sec)

            # Extract output
            output = None
            if hasattr(raw_result, "structured_content") and raw_result.structured_content:
                output = raw_result.structured_content.get("result", raw_result.structured_content)
            elif hasattr(raw_result, "content") and raw_result.content:
                # Text content
                text_items = [getattr(c, "text", str(c)) for c in raw_result.content]
                output = " ".join(text_items)
            else:
                output = raw_result

            is_error = getattr(raw_result, "is_error", False)
            if is_error:
                TOOL_ERRORS_TOTAL.labels(tool_name=tool_name, error_type="tool_error").inc()

            logger.info(
                f"Completed MCP tool '{tool_name}' in {duration_ms:.2f}ms",
                extra={
                    "event": "tool_execution_end",
                    "tool": tool_name,
                    "duration_ms": round(duration_ms, 2),
                    "status": "error" if is_error else "success",
                },
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                success=not is_error,
                output=output,
                duration_ms=round(duration_ms, 2),
                is_write=write_flag,
                requires_confirmation=write_flag,
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="failure").inc()
            TOOL_ERRORS_TOTAL.labels(tool_name=tool_name, error_type=type(exc).__name__).inc()

            logger.error(
                f"Error executing MCP tool '{tool_name}': {str(exc)}",
                extra={
                    "event": "tool_execution_error",
                    "tool": tool_name,
                    "duration_ms": round(duration_ms, 2),
                    "status": "failure",
                    "extra_data": {"error": str(exc)},
                },
            )

            return ToolExecutionResult(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                output=None,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                is_write=write_flag,
                requires_confirmation=write_flag,
            )
