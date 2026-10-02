"""Official Model Context Protocol (MCP) Server for Integration Copilot."""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from mcp.server.mcpserver import MCPServer

from mcp_server.tools.analytics import register_analytics_tools
from mcp_server.tools.customers import register_customer_tools
from mcp_server.tools.orders import register_order_tools
from mcp_server.tools.tickets import register_ticket_tools


def create_mcp_server() -> MCPServer:
    """Create and configure the MCP server with all enterprise business tools."""
    server = MCPServer("Integration Copilot Business Tools")

    # Register tool modules
    register_customer_tools(server)
    register_order_tools(server)
    register_ticket_tools(server)
    register_analytics_tools(server)

    return server


# Server instance for direct import
mcp_server = create_mcp_server()


def main():
    """Run MCP server in standard I/O mode for external agent/LLM hosts."""
    print("Starting Integration Copilot MCP server on stdio transport...", file=sys.stderr)
    mcp_server.run()


if __name__ == "__main__":
    main()
