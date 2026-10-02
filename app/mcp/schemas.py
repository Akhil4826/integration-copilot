"""MCP client schemas and tool execution representations."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    is_write: bool = False
    requires_confirmation: bool = False


class ToolExecutionResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    output: Any
    duration_ms: float
    error: Optional[str] = None
    is_write: bool = False
    requires_confirmation: bool = False
