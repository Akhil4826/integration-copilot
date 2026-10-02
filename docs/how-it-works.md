# How It Works: From Fundamentals to Advanced Architecture

This guide explains the entire system from the ground up. Whether you are learning about AI agents for the first time or preparing for a senior engineering interview, this document breaks down every concept step-by-step.

---

## 1. What Problem Are We Solving?

Traditional enterprise software requires human operators to click through multiple dashboards, write complex database queries, or copy-paste IDs between order management systems and support ticket desks.

For example, when a customer complains that their order is stuck, a support agent typically has to:
1. Search the customer database for their account ID.
2. Look up recent orders in an order service.
3. Filter for failed or delayed shipments.
4. Open the ticketing desk to create a high-priority ticket referencing the order ID.

**Integration Copilot** solves this by providing an intelligent assistant that understands natural English requests (e.g. *"Find failed orders for customer CUST-1004 and open a high-priority ticket for the latest one"*), figures out the sequence of actions, retrieves the exact business data, and safely drafts the actions with human confirmation.

---

## 2. Core Concepts Explained Simply

### What is an API?
An **API (Application Programming Interface)** is a structured way for programs to talk to each other. Instead of a human looking at a webpage, code sends a structured request (like `GET /api/v1/orders?status=FAILED`) and receives structured data back (like JSON).

### What is an LLM?
A **Large Language Model (LLM)** is a statistical text-completion engine trained on vast amounts of language. It does not possess a live connection to your private database or company systems. By default, if you ask it *"What were our sales today?"*, it cannot know unless that information is provided in its prompt.

### What is an Agent?
An **AI Agent** is an architecture where an LLM is given reasoning abilities and access to tools. Instead of merely answering questions from static memory, the agent:
1. Receives a user goal.
2. Evaluates what information or actions are missing.
3. Chooses a tool to execute.
4. Reads the tool output.
5. Repeats the process until the goal is achieved.

### What is Tool Calling?
**Tool calling** (or function calling) is a mechanism where an LLM is provided with descriptions of functions (names, descriptions, and expected parameters in JSON Schema). 

When the model decides it needs data, instead of returning conversational text, it returns a structured tool call:
```json
{
  "name": "search_orders",
  "arguments": { "status": "FAILED" }
}
```
The application code intercepts this JSON, runs the actual Python function, and returns the result to the LLM.

### What is MCP (Model Context Protocol)?
**MCP** is an open standard that unifies how applications expose tools and context to AI models. 
- Without MCP, every developer invents their own proprietary way to format tool dictionaries, parse responses, and handle errors.
- With MCP, tools follow an open standard. Any MCP-compatible client can query an MCP server to discover tools, inspect their schemas, and execute them safely.

### What is an MCP Server?
An **MCP Server** is an application that registers tools, resources, and prompt templates, making them available over standard communication channels (like JSON-RPC, standard I/O, or in-process calls). In this project, `mcp_server/server.py` hosts 13 business tools for customers, orders, tickets, and analytics.

### What is Ollama?
**Ollama** is an open-source tool that allows developers to run open-weight Large Language Models (like Qwen, Llama, Mistral) locally on their own computer (CPU or GPU) completely free without sending data to third-party cloud providers.

---

## 3. End-to-End Walkthrough of a Request

Let us trace a concrete query from start to finish:
**User Prompt:** *"Show me all failed orders."*

### Step 1: User to FastAPI Gateway
1. The user types the message into the Web UI.
2. The browser JavaScript sends an HTTP POST request:
   ```http
   POST /api/v1/agent/chat HTTP/1.1
   Authorization: Bearer development-token
   Content-Type: application/json

   {
     "message": "Show me all failed orders."
   }
   ```
3. FastAPI intercepts the request:
   - Verifies the Bearer token (`app/core/security.py`).
   - Checks the sliding-window rate limit (30 requests/minute).
   - Generates a unique `request_id` (e.g. `req_9f3b...`) and `execution_id` (e.g. `exec_1a8d...`).

### Step 2: The Agent Prepares Context
1. The `AgentService` initializes the `Planner`.
2. The planner queries the `MCPClient` for all registered tools via `list_tools()`.
3. The client returns tool definitions formatted as JSON schemas, including `search_orders`, `get_customer`, `create_support_ticket`, etc.
4. The agent loads the system prompt (`app/agent/prompts.py`), which instructs the model on anti-hallucination, grounding, and tool usage rules.

### Step 3: LLM Decides to Call a Tool
1. The agent passes the message history and tool schemas to the `LLMProvider` (`OllamaProvider` or `MockLLMProvider`).
2. The model analyzes the user query *"Show me all failed orders"*.
3. It determines that `search_orders` with argument `status="FAILED"` matches the intent.
4. The model returns:
   ```json
   {
     "content": null,
     "tool_calls": [
       {
         "name": "search_orders",
         "arguments": { "status": "FAILED" }
       }
     ]
   }
   ```

### Step 4: Tool Execution Reaches SQLite
1. The `ToolExecutor` inspects the tool call:
   - Is it a WRITE tool? No, `search_orders` is a READ tool. Proceed.
2. The executor calls `mcp_client.call_tool("search_orders", {"status": "FAILED"})`.
3. The MCP Server executes the tool function `mcp_server/tools/orders.py:search_orders`:
   - Validates arguments using Pydantic `OrderFilterParams`.
   - Opens a database session via SQLAlchemy.
   - Calls `OrderService.list_orders()`, which delegates to `OrderRepository`.
   - The repository executes a parameterized SQL query:
     ```sql
     SELECT * FROM orders WHERE status = 'FAILED' ORDER BY created_at DESC LIMIT 10;
     ```
   - SQLite returns 8 matching order records.
4. The tool serializes the records into a structured JSON payload:
   ```json
   {
     "total": 8,
     "orders": [
       { "order_id": "ORD-1005", "customer_id": "CUST-1004", "total_amount": 249.99, ... },
       ...
     ]
   }
   ```

### Step 5: Returning the Result to the LLM
1. The tool result is packaged into an `LLMMessage` with role `"tool"` and the matching `tool_call_id`.
2. The agent appends this message to the conversation history.
3. The agent calls the LLM again:
   - Prompt includes: System prompt + User request + Model's tool call + Tool result data.
4. The model reads the actual database records and synthesizes a natural English response:
   > *"I found 8 failed orders in the database. The most recent one is ORD-1005 for customer CUST-1004 totaling $249.99..."*

### Step 6: Final Response & Observability
1. The agent compiles the `AgentResponse`:
   - `response`: The synthesized answer.
   - `tool_trace`: The exact audit record (tool name `search_orders`, duration `12.4ms`, status `success`).
   - `execution_id`: The trace ID.
2. Structured JSON logs are emitted.
3. Prometheus metrics (`agent_requests_total`, `tool_calls_total`, `tool_execution_duration_seconds`) are incremented.
4. The Web UI renders the response and populates the expandable **Execution Details** accordion.

---

## 4. How Human Confirmation Works for Writes

What happens when the user asks:
*"Create a support ticket for customer CUST-1004: order is delayed"*?

1. The LLM selects `create_support_ticket`.
2. The `ToolExecutor` checks its classification: `create_support_ticket` is in `WRITE_TOOLS`.
3. **Execution is immediately halted before touching the database**.
4. The backend generates a secure, one-time confirmation token:
   ```json
   {
     "requires_confirmation": true,
     "confirmation": {
       "confirmation_token": "c71e2b...",
       "action_summary": "Create support ticket for customer CUST-1004",
       "tool_name": "create_support_ticket",
       "arguments": {
         "customer_id": "CUST-1004",
         "title": "Order is delayed",
         "priority": "HIGH"
       },
       "expires_at": "2026-10-02T23:45:00Z"
     }
   }
   ```
5. The Web UI displays an approval card with the exact arguments and `[Confirm Action]` / `[Cancel]` buttons.
6. The write only executes if the client submits `confirmed=True` with the matching token before expiration.
7. This completely prevents prompt injection attacks or rogue autonomous models from altering company data.
