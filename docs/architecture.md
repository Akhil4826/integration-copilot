# System Architecture

## Overview

**Integration Copilot** is built upon a layered, decoupled architecture designed to bridge natural language requests to structured business operations with zero cloud dependencies. It demonstrates how modern AI applications can safely interact with core enterprise services through standardized protocols, strict type validation, and human-in-the-loop safeguards.

```mermaid
graph TD
    User([User / Browser UI]) <-->|HTTP / REST| API[FastAPI Gateway]
    
    subgraph "Application Core"
        API --> Security[Security & Rate Limiting]
        Security --> AgentService[Agent Orchestration Service]
        AgentService --> Planner[Agent Planner Loop]
        Planner <--> LLM[LLM Provider: Ollama / Mock]
        Planner --> Executor[Tool Execution Engine]
        Executor --> ConfirmStore[Confirmation Store]
    end

    subgraph "Model Context Protocol (MCP)"
        Executor <-->|In-Memory / Dynamic Discovery| MCPClient[MCP Client]
        MCPClient <-->|Call Tool / Schemas| MCPServer[Official MCP Server]
        MCPServer --> CustomerTools[Customer Tools]
        MCPServer --> OrderTools[Order Tools]
        MCPServer --> TicketTools[Ticket Tools]
        MCPServer --> AnalyticsTools[Analytics Tools]
    end

    subgraph "Domain & Persistence"
        CustomerTools --> Services[Business Services]
        OrderTools --> Services
        TicketTools --> Services
        AnalyticsTools --> Services
        Services --> Repos[Repository Layer]
        Repos --> SQLite[(SQLite Database)]
    end

    subgraph "Observability"
        API -.-> Metrics[Prometheus Metrics]
        AgentService -.-> JSONLogs[Structured JSON Logs]
    end
```

---

## Architectural Layers & Separation of Concerns

1. **API Layer (`app/api/`)**:
   - Exposes RESTful endpoints for CRUD operations and AI interactions.
   - Handles HTTP serialization, status codes, query parameter validation, and rate limiting (sliding window 30 req/min).
   - Injects dependencies (database sessions, domain services, security principals).

2. **Agent Layer (`app/agent/`)**:
   - Orchestrates multi-step reasoning without allowing the model direct database access.
   - Manages execution limits (`MAX_AGENT_STEPS = 8`) to guarantee termination.
   - Detects high-consequence write operations and enforces cryptographic confirmation tokens.

3. **LLM Provider Layer (`app/llm/`)**:
   - Abstract interface (`LLMProvider`) decoupling the agent from specific model backends.
   - Implementations:
     - `OllamaProvider`: Local inference over HTTP with exponential backoff retries.
     - `MockLLMProvider`: Deterministic, zero-network rule-based provider for CI/CD and unit testing.

4. **MCP Layer (`app/mcp/` & `mcp_server/`)**:
   - Standardized tool abstraction using the official Python MCP SDK.
   - Exposes 13 validated business tools with strict JSON schemas.
   - Client dynamically queries the server for tools rather than hardcoding function signatures.

5. **Service Layer (`app/services/`)**:
   - Houses business logic, invariants, and transaction boundaries.
   - Calculates order totals, validates stock, and handles entity transitions.

6. **Repository Layer (`app/repositories/`)**:
   - Isolates SQLAlchemy ORM queries and database access patterns.
   - Implements parameterized filters, sorting, and pagination.

7. **Database Layer (`app/models/` & `app/db/`)**:
   - SQLAlchemy 2.0 declarative models.
   - Alembic schema migrations.
   - Deterministic relational schema across Customers, Products, Orders, Order Items, and Support Tickets.

8. **Observability Layer (`app/core/logging.py`, `app/core/metrics.py`)**:
   - Request-scoped tracking (`request_id` and `execution_id`).
   - Standardized structured JSON output.
   - Prometheus metrics endpoint at `/metrics`.

---

## Key System Flows

### 1. Read-Only Query Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Web UI / Client
    participant API as FastAPI Router
    participant Agent as Agent Service
    participant LLM as Ollama / Mock LLM
    participant MCP as MCP Server
    participant DB as SQLite Database

    User->>UI: "Show me all failed orders"
    UI->>API: POST /api/v1/agent/chat (Bearer Token)
    API->>Agent: process_request(message, execution_id)
    Agent->>LLM: generate_with_tools(messages, tools)
    LLM-->>Agent: LLMResponse(tool_calls=[search_orders(status="FAILED")])
    Agent->>MCP: call_tool("search_orders", status="FAILED")
    MCP->>DB: SELECT * FROM orders WHERE status = 'FAILED'
    DB-->>MCP: [ORD-1005, ORD-1012, ...]
    MCP-->>Agent: ToolResult(items=[...], count=8)
    Agent->>LLM: generate(tool_result_messages)
    LLM-->>Agent: LLMResponse("Found 8 failed orders...")
    Agent-->>API: AgentResponse(response="...", tool_trace=[...])
    API-->>UI: 200 OK JSON
    UI-->>User: Render Message + Tool Trace Accordion
```

### 2. Human-in-the-Loop Write Confirmation Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Web UI / Client
    participant API as FastAPI Router
    participant Agent as Agent Service
    participant LLM as LLM Provider
    participant CStore as Confirmation Store
    participant MCP as MCP Server
    participant DB as SQLite Database

    User->>UI: "Create high priority ticket for CUST-1004: Order delayed"
    UI->>API: POST /api/v1/agent/chat
    API->>Agent: process_request()
    Agent->>LLM: generate_with_tools()
    LLM-->>Agent: tool_call("create_support_ticket", {...})
    Note over Agent: Detected WRITE tool! Intercept execution.
    Agent->>CStore: create_token(tool="create_support_ticket", args={...})
    CStore-->>Agent: confirmation_token ("c0af..."), expires_at
    Agent-->>API: AgentResponse(requires_confirmation=True, confirmation={...})
    API-->>UI: 200 OK (Pending Confirmation)
    UI-->>User: Display Action Summary + [Confirm] [Cancel]

    User->>UI: Clicks [Confirm Action]
    UI->>API: POST /api/v1/agent/chat (confirmation_token="c0af...", confirmed=True)
    API->>Agent: confirm_and_execute(token)
    Agent->>CStore: consume_token("c0af...")
    CStore-->>Agent: Valid Action ({tool: "create_support_ticket", ...})
    Agent->>MCP: call_tool("create_support_ticket", args)
    MCP->>DB: INSERT INTO support_tickets ...
    DB-->>MCP: Created TCK-1031
    MCP-->>Agent: ToolResult(ticket_id="TCK-1031", status="OPEN")
    Agent-->>API: AgentResponse(response="Ticket TCK-1031 created.")
    API-->>UI: 200 OK
    UI-->>User: Show Success + Ticket Details
```

### 3. Multi-Step Workflow

```mermaid
flowchart TD
    Start([User: 'Find failed orders for CUST-1004 and open ticket']) --> Step1[Step 1: Check Customer Orders]
    Step1 --> Tool1[Call get_customer_orders CUST-1004]
    Tool1 --> Inspect[Agent Inspects Result: Found ORD-1012 FAILED]
    Inspect --> Step2[Step 2: Prepare Support Ticket]
    Step2 --> Guard{Is Tool Consequential Write?}
    Guard -- Yes --> Token[Generate Secure Token & Intercept]
    Token --> AskUser[Request Human Confirmation via UI]
    AskUser --> UserInput{User Confirms?}
    UserInput -- Approved --> Execute[Execute MCP create_support_ticket]
    Execute --> Complete([Return Final Ticket ID to User])
    UserInput -- Rejected --> Cancel([Aborted safely without DB write])
```

### 4. Error Handling & Guardrail Protection

```mermaid
flowchart TD
    Req[Incoming Agent Request] --> LoopCheck{Step Count > MAX_AGENT_STEPS?}
    LoopCheck -- Yes (Exceeded 8) --> AbortLoop[Return 200 with step_limit_exceeded error]
    LoopCheck -- No --> ToolExec[Execute Discovered MCP Tool]
    ToolExec --> ToolTry{Tool Succeeded?}
    ToolTry -- Yes --> NextStep[Feed Result to Model Context]
    ToolTry -- No (Validation / DB Error) --> FormattedError[Format Safe Error Payload without Stack Trace]
    FormattedError --> FeedModel[Feed Structured Error to LLM]
    FeedModel --> SafeAnswer[LLM Explains Error to User Gracefully]
```
