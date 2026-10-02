"""Executes validated MCP tools, handles safe trace summarization and confirmation gating."""

from typing import Any, Dict, Optional, Tuple

from app.agent.schemas import ToolTraceEntry
from app.core.logging import logger
from app.mcp.client import MCPClient
from app.mcp.schemas import ToolExecutionResult
from mcp_server.schemas import is_write_tool


def generate_safe_summary(tool_name: str, arguments: Dict[str, Any], output: Any) -> str:
    """Produce a safe, concise execution summary for display without raw data dumps."""
    if isinstance(output, dict) and output.get("error"):
        return f"Error: {output['error']}"

    if tool_name == "get_customer":
        if isinstance(output, dict) and output.get("name"):
            return f"Found customer {output.get('customer_id')} ({output.get('name')})"
        return "Customer not found"

    elif tool_name == "search_customers":
        if isinstance(output, dict):
            return f"Found {output.get('count', 0)} matching customer(s)"
        return "Customer search completed"

    elif tool_name == "get_order":
        if isinstance(output, dict) and output.get("order_id"):
            return f"Order {output.get('order_id')} found (Status: {output.get('status')}, Total: ${output.get('total_amount', 0):.2f})"
        return "Order details retrieved"

    elif tool_name == "search_orders":
        if isinstance(output, dict):
            return f"Retrieved {output.get('count', 0)} order(s) (Status filter: {arguments.get('status', 'ANY')})"
        return "Orders query completed"

    elif tool_name == "get_customer_orders":
        if isinstance(output, dict):
            return f"Retrieved {output.get('count', 0)} order(s) for customer {arguments.get('customer_id')}"
        return "Customer orders query completed"

    elif tool_name == "create_support_ticket":
        if isinstance(output, dict) and output.get("ticket_id"):
            return f"Created ticket {output.get('ticket_id')} (Priority: {output.get('priority')})"
        return "Support ticket created"

    elif tool_name == "update_support_ticket":
        if isinstance(output, dict) and output.get("ticket_id"):
            return f"Updated ticket {output.get('ticket_id')} status"
        return "Support ticket updated"

    elif tool_name == "get_support_ticket":
        if isinstance(output, dict) and output.get("ticket_id"):
            return f"Ticket {output.get('ticket_id')} found ({output.get('priority')}, {output.get('status')})"
        return "Ticket retrieved"

    elif tool_name == "list_support_tickets":
        if isinstance(output, dict):
            return f"Retrieved {output.get('count', 0)} ticket(s)"
        return "Support tickets listed"

    elif tool_name == "get_order_statistics":
        if isinstance(output, dict):
            return f"Aggregated stats: {output.get('total_orders')} orders, ${output.get('total_revenue', 0):.2f} revenue"
        return "Order statistics calculated"

    elif tool_name == "get_top_products":
        if isinstance(output, dict):
            return f"Retrieved top {output.get('count', 0)} products by sales revenue"
        return "Top products retrieved"

    elif tool_name == "create_order":
        if isinstance(output, dict) and output.get("order_id"):
            return f"Order {output.get('order_id')} placed successfully (${output.get('total_amount', 0):.2f})"
        return "Order placed"

    elif tool_name == "update_order_status":
        if isinstance(output, dict) and output.get("order_id"):
            return f"Order {output.get('order_id')} updated to {output.get('status')}"
        return "Order status updated"

    return f"Executed {tool_name} successfully"


class ToolExecutor:
    """Manages MCP tool execution, confirmation checks, and trace formatting."""

    def __init__(self, mcp_client: Optional[MCPClient] = None):
        self.mcp_client = mcp_client or MCPClient()

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        step_number: int,
        allow_write: bool = False,
    ) -> Tuple[Optional[ToolExecutionResult], Optional[ToolTraceEntry], bool]:
        """Execute tool or signal that confirmation is required.

        Returns:
            (ToolExecutionResult or None, ToolTraceEntry or None, requires_confirmation: bool)
        """
        if is_write_tool(tool_name) and not allow_write:
            # Intercept: requires confirmation
            logger.info(
                f"Write tool '{tool_name}' requires human confirmation",
                extra={"event": "confirmation_intercepted", "tool": tool_name},
            )
            return None, None, True

        result = await self.mcp_client.execute_tool(tool_name, arguments)
        summary = generate_safe_summary(
            tool_name, arguments, result.output if result.success else result.error
        )

        trace_entry = ToolTraceEntry(
            step=step_number,
            tool=tool_name,
            arguments=arguments,
            duration_ms=result.duration_ms,
            status="success" if result.success else "error",
            result_summary=summary,
        )

        return result, trace_entry, False
