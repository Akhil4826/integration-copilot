# 5-Minute Live Portfolio Demo Script

This document provides a step-by-step walkthrough script for demonstrating **Integration Copilot** in a live software engineering interview or presentation.

---

## 1. Prerequisites Checklist (1 Minute Before Demo)

1. **Terminal 1: Start Ollama** (or use `LLM_PROVIDER=mock` if presenting in a lightweight environment):
   ```powershell
   ollama run qwen3:4b
   ```
2. **Terminal 2: Start the FastAPI Server**:
   ```powershell
   .venv\Scripts\Activate.ps1
   uvicorn app.main:app --reload --port 8000
   ```
3. Open your browser to:
   - Web Copilot UI: [http://localhost:8000](http://localhost:8000)
   - Interactive Swagger API: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Prometheus Metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)

---

## 2. Step-by-Step Demo Script (5 Minutes)

### Phase 1: High-Level Introduction (30 Seconds)
- **Say**: *"This is Integration Copilot, an AI-powered enterprise assistant built with FastAPI, Ollama, and Model Context Protocol (MCP). It bridges conversational requests to enterprise systems with human-in-the-loop write safety."*
- **Action**: Open [http://localhost:8000](http://localhost:8000). Show the clean dark-mode UI with the system readiness indicators showing **System: Operational**, **Model: qwen3:4b**, **MCP: 13 Tools Loaded**.

---

### Phase 2: Read Query & Tool Execution Trace (1 Minute)
- **Prompt**: Type into chat:
  ```text
  Show me all failed orders.
  ```
- **Say**: *"Notice that the model didn't just generate generic text. It dynamically selected the `search_orders` MCP tool with parameter `status='FAILED'`."*
- **Action**:
  - Show the response listing the 8 failed orders from the deterministic SQLite seed.
  - Expand the **Execution Details** accordion beneath the message.
  - Point out:
    - **Tool**: `search_orders`
    - **Execution ID**: `exec_...`
    - **Latency**: ~15ms
    - **Status**: `success`

---

### Phase 3: Multi-Entity Customer Query (1 Minute)
- **Prompt 1**:
  ```text
  Find customer CUST-1004.
  ```
- **Say**: *"The agent invoked `get_customer` to retrieve customer details for CUST-1004."*
- **Prompt 2**:
  ```text
  Show me the orders for customer CUST-1004.
  ```
- **Say**: *"Here the agent called `get_customer_orders`. We see the customer has a failed order, ORD-1005."*

---

### Phase 4: Human-in-the-Loop Write Confirmation (1.5 Minutes)
- **Prompt**:
  ```text
  Create a high priority support ticket for customer CUST-1004 saying their order is delayed.
  ```
- **Say**: *"Now watch what happens when we ask the model to perform a state mutation. The system classifies `create_support_ticket` as a WRITE tool. Instead of blindly writing to the database, execution is intercepted."*
- **Action**:
  - Point to the **Pending Action Confirmation** card rendered in the chat.
  - Highlight the proposed action, customer ID (`CUST-1004`), priority (`HIGH`), and title.
  - Click **[Confirm Action]**.
  - Show the immediate ticket creation response with the generated ticket ID (e.g. `TCK-1031`).
  - Explain: *"A one-time cryptographic confirmation token was redeemed. This prevents prompt injection attacks or autonomous hallucinations from modifying production data without approval."*

---

### Phase 5: REST API & Architecture (30 Seconds)
- **Action**: Switch tabs to [http://localhost:8000/docs](http://localhost:8000/docs).
- **Say**: *"Under the hood, all business services are exposed as typed REST endpoints with Pydantic validation, filtering, pagination, and OpenAPI documentation."*

---

### Phase 6: Code Quality, Tests & Evaluation (1 Minute)
- **Action**: Switch to Terminal and run the test suite:
  ```powershell
  pytest --cov=app --cov=mcp_server
  ```
  - **Highlight**: 52 passed tests, **85% test coverage**!
- **Action**: Run the agent evaluation benchmark:
  ```powershell
  python -m evaluation.run
  ```
  - **Highlight**: 16 evaluation benchmark cases with **100% pass rate**, **100% tool selection accuracy**, and **100% confirmation compliance**.

---

## 3. Wrap-up Summary
> *"In summary, this project demonstrates clean layered architecture, tool calling using the official MCP Python SDK, safe human-in-the-loop workflows, comprehensive unit testing, and full observability—all running 100% locally for free."*
