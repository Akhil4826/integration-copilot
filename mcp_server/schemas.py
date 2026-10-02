"""MCP tool schemas, classifications, and metadata."""

from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel


class ToolCategory(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


WRITE_TOOLS = {
    "create_support_ticket",
    "update_support_ticket",
    "create_order",
    "update_order_status",
}

READ_TOOLS = {
    "get_customer",
    "search_customers",
    "get_order",
    "search_orders",
    "get_customer_orders",
    "get_support_ticket",
    "list_support_tickets",
    "get_order_statistics",
    "get_top_products",
}


def is_write_tool(tool_name: str) -> bool:
    """Return True if tool performs state mutation requiring confirmation."""
    return tool_name in WRITE_TOOLS


class MCPToolMetadata(BaseModel):
    name: str
    description: str
    category: ToolCategory
    requires_confirmation: bool
    parameters_schema: Dict[str, Any]
