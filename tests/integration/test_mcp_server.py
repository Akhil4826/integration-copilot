"""Integration tests for MCP Server and Client."""

import pytest

from app.mcp.client import MCPClient
from mcp_server.schemas import is_write_tool
from mcp_server.server import mcp_server


class TestMCPServerIntegration:
    @pytest.mark.asyncio
    async def test_tool_discovery_count_and_schemas(self):
        client = MCPClient(server=mcp_server)
        tools = await client.discover_tools(force_refresh=True)
        assert len(tools) >= 13

        tool_names = {t.name for t in tools}
        assert "get_customer" in tool_names
        assert "search_orders" in tool_names
        assert "create_support_ticket" in tool_names
        assert "get_order_statistics" in tool_names
        assert "get_top_products" in tool_names

    @pytest.mark.asyncio
    async def test_read_tools_execution(self):
        client = MCPClient(server=mcp_server)

        # 1. get_customer
        res = await client.execute_tool("get_customer", {"customer_id": "CUST-1004"})
        assert res.success
        assert res.output["customer_id"] == "CUST-1004"
        assert not is_write_tool("get_customer")

        # 2. search_orders
        res_orders = await client.execute_tool("search_orders", {"status": "FAILED", "limit": 5})
        assert res_orders.success
        assert res_orders.output["total_matches"] >= 10
        assert len(res_orders.output["orders"]) <= 5

        # 3. get_order_statistics
        res_stats = await client.execute_tool("get_order_statistics", {})
        assert res_stats.success
        assert res_stats.output["total_orders"] == 100
        assert res_stats.output["total_revenue"] > 0

    @pytest.mark.asyncio
    async def test_write_tool_execution(self):
        client = MCPClient(server=mcp_server)
        assert is_write_tool("create_support_ticket")

        res = await client.execute_tool(
            "create_support_ticket",
            {
                "customer_id": "CUST-1004",
                "order_id": "ORD-1004",
                "title": "MCP write tool integration test",
                "description": "Verifying ticket creation via MCP protocol invocation",
                "priority": "HIGH",
            },
        )
        assert res.success
        assert res.output["ticket_id"].startswith("TCK-")
        assert res.is_write
        assert res.requires_confirmation

    @pytest.mark.asyncio
    async def test_all_remaining_mcp_tools(self):
        client = MCPClient(server=mcp_server)

        # search_customers
        res_sc = await client.execute_tool("search_customers", {"query": "Jennifer"})
        assert res_sc.success
        assert res_sc.output["count"] >= 1

        # get_order
        res_go = await client.execute_tool("get_order", {"order_id": "ORD-1004"})
        assert res_go.success
        assert res_go.output["order_id"] == "ORD-1004"

        # get_customer_orders
        res_co = await client.execute_tool("get_customer_orders", {"customer_id": "CUST-1004"})
        assert res_co.success
        assert res_co.output["count"] >= 1

        # create_order
        res_ord = await client.execute_tool(
            "create_order",
            {"customer_id": "CUST-1001", "product_id": "PROD-1001", "quantity": 3},
        )
        assert res_ord.success
        assert res_ord.output["order_id"].startswith("ORD-")

        # update_order_status
        res_uord = await client.execute_tool(
            "update_order_status",
            {"order_id": "ORD-1001", "status": "DELIVERED"},
        )
        assert res_uord.success
        assert res_uord.output["status"] == "DELIVERED"

        # get_support_ticket
        res_gt = await client.execute_tool("get_support_ticket", {"ticket_id": "TCK-1001"})
        assert res_gt.success
        assert res_gt.output["ticket_id"] == "TCK-1001"

        # list_support_tickets
        res_lt = await client.execute_tool("list_support_tickets", {"status": "OPEN", "limit": 5})
        assert res_lt.success
        assert len(res_lt.output["tickets"]) >= 1

        # update_support_ticket
        res_ut = await client.execute_tool(
            "update_support_ticket",
            {"ticket_id": "TCK-1001", "status": "RESOLVED"},
        )
        assert res_ut.success
        assert res_ut.output["status"] == "RESOLVED"

    @pytest.mark.asyncio
    async def test_invalid_tool_arguments_handled_gracefully(self):
        client = MCPClient(server=mcp_server)
        res = await client.execute_tool("search_orders", {"status": "INVALID_STATUS_NAME"})
        assert res.output.get("code") == "INVALID_STATUS"
