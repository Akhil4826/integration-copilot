# Portfolio Screenshots Guide

To showcase this project in your GitHub repository and portfolio, capture the following 8 screenshots and place them in this directory (`docs/screenshots/`):

---

## Required Screenshots Checklist

### 1. `01-main-ai-interface.png`
- **What to capture**: The main chat interface at `http://localhost:8000` with dark mode active.
- **Content**: An active conversation showing a user query (e.g. *"Show me all failed orders"* or *"What are the top 5 products by sales?"*), the assistant's structured answer, and the top status badges (**System: Operational**, **Model: qwen3:4b**, **MCP: 13 Tools Loaded**).

### 2. `02-tool-execution-trace.png`
- **What to capture**: An expanded view of the **Execution Details** accordion beneath an assistant response.
- **Content**: Shows the tool name (`search_orders` or `get_order_statistics`), the Execution ID (`exec_...`), the latency measurement in milliseconds (e.g. `14.2ms`), and the successful completion status.

### 3. `03-confirmation-flow.png`
- **What to capture**: The **Pending Action Confirmation** card rendered in the chat when the user requests a write operation (e.g. *"Create a high-priority support ticket for customer CUST-1004 saying their order is delayed"*).
- **Content**: Shows the warning badge, the extracted parameters (Customer ID, Priority, Title, Description), and the `[Confirm Action]` and `[Cancel]` buttons before execution.

### 4. `04-swagger-api-docs.png`
- **What to capture**: The FastAPI Swagger UI at `http://localhost:8000/docs`.
- **Content**: Show the organized route tags: **Customers**, **Orders**, **Support Tickets**, **Analytics**, **AI Agent**, **Health**, and **Metrics**. Expand one of the order endpoints showing parameter documentation.

### 5. `05-mcp-tools-view.png`
- **What to capture**: An inspect view or terminal showing the 13 discovered MCP tools, or the `/docs` documentation highlighting the tool schema endpoints.
- **Content**: Tools list showing `get_customer`, `search_orders`, `create_support_ticket`, `get_top_products`, etc.

### 6. `06-database-tables.png`
- **What to capture**: SQLite database opened in a viewer like **DB Browser for SQLite**, **VS Code SQLite Viewer**, or `scripts/seed_db.py` output.
- **Content**: Tables showing the seeded data (30 customers, 50 products, 100 orders, 30 support tickets).

### 7. `07-evaluation-report.png`
- **What to capture**: The terminal output after running:
  ```powershell
  python -m evaluation.run
  ```
- **Content**: The benchmark summary report showing:
  - Total Test Cases: 16
  - Passed: 16
  - Pass Rate: 100.0%
  - Tool Selection Accuracy: 100.0%
  - Confirmation Compliance: 100.0%
  - Anti-Hallucination Rate: 100.0%

### 8. `08-github-actions-ci.png`
- **What to capture**: The GitHub Actions tab on your repository after pushing.
- **Content**: The green checkmark next to the CI workflow showing passing steps:
  - `Run Ruff Linter & Format Check`
  - `Run Mypy Type Checker`
  - `Run Unit & Integration Tests (pytest)`
  - `Run Agent Evaluation Benchmark`
  - `Build Docker Container`
