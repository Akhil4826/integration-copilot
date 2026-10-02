# Model Context Protocol (MCP) Integration

## 1. What is the Model Context Protocol?

The **Model Context Protocol (MCP)** is an open standard introduced by Anthropic that standardizes how AI applications provide tools, prompt templates, and data context to Large Language Models.

### Traditional Custom Tool Calling vs. MCP

| Feature | Ad-Hoc / Custom Tool Calling | Model Context Protocol (MCP) |
|---|---|---|
| **Interface** | Hardcoded dictionaries per provider (OpenAI, Anthropic, Ollama format) | Standardized client-server protocol with JSON Schema definitions |
| **Coupling** | The agent code is tightly bound to internal API code | Tools run as a standalone server or decoupled component |
| **Discovery** | Tools are manually defined in prompts or application dicts | Client dynamically queries `list_tools()` at runtime |
| **Composability** | Difficult to reuse tools across multiple AI frontends/IDE agents | Any MCP-compliant client (Claude Desktop, Antigravity IDE, custom clients) can consume the tools |
| **Security Boundaries** | Tools execute inside the agent's application memory space | Can run out-of-process, with isolated process permissions and audit logging |

MCP does not magically make an AI model smarter; rather, it **standardizes how models discover, validate, and execute capabilities**, transforming fragmented scripts into composable tool platforms.

---

## 2. Why Integration Copilot Uses MCP

1. **Standardized Tool Contracts**: Instead of manually formatting JSON schemas for every LLM provider, MCP provides first-class schema validation using standard JSON Schema / Pydantic.
2. **Dynamic Capability Discovery**: When new tools are added to `mcp_server/tools/`, the agent automatically discovers them via `mcp_client.list_tools()` without needing code changes in the planning loop.
3. **Decoupled Architecture**: The MCP server can run in-memory within the backend process, over stdio, or as an independent microservice container across an internal network.

---

## 3. Server Architecture (`mcp_server/`)

The server is implemented using the official Python MCP SDK:
- Core Server: `mcp_server/server.py` creates an `MCPServer("integration-copilot-tools")` instance.
- Tool Registration: Modular decorators (`@server.tool()`) across domain modules:
  - `mcp_server/tools/customers.py`
  - `mcp_server/tools/orders.py`
  - `mcp_server/tools/tickets.py`
  - `mcp_server/tools/analytics.py`

### Tool Registry Summary (13 Production Tools)

| Category | Tool Name | Mode | Purpose | Key Inputs |
|---|---|---|---|---|
| **Customers** | `get_customer` | READ | Fetch single customer by ID | `customer_id: str` |
| **Customers** | `search_customers` | READ | Filter customers by text query | `query: str`, `limit: int` |
| **Orders** | `get_order` | READ | Fetch order details & items | `order_id: str` |
| **Orders** | `search_orders` | READ | Filter orders by status/date/amount | `status`, `start_date`, `end_date`, `limit` |
| **Orders** | `get_customer_orders`| READ | List all orders for a customer | `customer_id: str`, `limit: int` |
| **Orders** | `create_order` | WRITE | Create a new order with items | `customer_id`, `items: list`, `status` |
| **Orders** | `update_order_status`| WRITE | Update status of an existing order | `order_id: str`, `status: str` |
| **Tickets** | `get_support_ticket` | READ | Retrieve ticket by ID | `ticket_id: str` |
| **Tickets** | `list_support_tickets`| READ | Filter tickets by status/priority | `status`, `priority`, `customer_id` |
| **Tickets** | `create_support_ticket`| WRITE | Create support ticket | `customer_id`, `title`, `description`, `priority` |
| **Tickets** | `update_support_ticket`| WRITE | Update ticket priority/status | `ticket_id`, `priority`, `status`, `description` |
| **Analytics** | `get_order_statistics`| READ | Aggregate order counts and revenue | `start_date`, `end_date` |
| **Analytics** | `get_top_products` | READ | Top revenue products | `limit: int` |

---

## 4. MCP Client Architecture (`app/mcp/client.py`)

The application's `MCPClient` connects to the tool server:
1. **Tool Discovery**:
   ```python
   tools = await mcp_client.list_tools()
   ```
   Retrieves tool names, descriptions, and input schemas, transforming them into the format expected by the LLM Provider.
2. **Tool Execution**:
   ```python
   result = await mcp_client.call_tool(
       tool_name="get_customer", arguments={"customer_id": "CUST-1004"}
   )
   ```
   Records execution latency, updates Prometheus counter `tool_calls_total`, and wraps errors in structured payloads.

---

## 5. Security & Read vs. Write Governance

To prevent autonomous destructive changes, tools are classified into **READ** and **WRITE**:
- **READ Tools**: Run immediately without side-effects.
- **WRITE Tools**: (`create_support_ticket`, `update_support_ticket`, `create_order`, `update_order_status`).
  - When the agent selects a WRITE tool, execution is **intercepted**.
  - A secure confirmation token is generated and returned to the caller with a preview of the proposed payload.
  - The tool is executed **only after** an authorized user posts a confirmation payload.

---

## 6. How to Test the MCP Tools

### Running Deterministic MCP Tests
The repository includes dedicated tests for every MCP tool:
```powershell
pytest tests/unit/test_mcp_tools.py -v
```

### Manual Testing via Python Interactive Shell
```python
import asyncio
from app.mcp.client import get_mcp_client


async def test():
    client = get_mcp_client()
    tools = await client.list_tools()
    print(f"Discovered {len(tools)} tools")

    res = await client.call_tool("get_customer", {"customer_id": "CUST-1004"})
    print("Result:", res)


asyncio.run(test())
```
