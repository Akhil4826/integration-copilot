# Technical Interview Guide & Pitch Deck

This guide prepares you to speak about **Integration Copilot** with confidence during technical interviews, system design rounds, and hiring manager conversations.

---

## 1. Project Pitches

### The 2-Minute Elevator Pitch
> *"Integration Copilot is a production-style business API assistant that bridges natural language requests to real enterprise databases and services. Instead of building a generic chatbot, I built an AI agent using FastAPI, local LLMs via Ollama, and Anthropic's Model Context Protocol (MCP). The agent dynamically discovers business tools, executes parameterized SQL queries against an e-commerce database, and enforces strict security controls—including human-in-the-loop confirmation tokens for write actions, sliding-window rate limiting, loop guards, and Prometheus observability. Everything runs locally with zero external API costs, accompanied by an automated evaluation framework testing tool selection and anti-hallucination behavior."*

### The 5-Minute Technical Overview
> *"When building AI applications for enterprise environments, two major issues arise: vendor lock-in with proprietary tool-calling formats, and the dangerous risk of autonomous LLMs executing destructive writes. I designed Integration Copilot around three architectural pillars:*
> 1. *Standardized Tooling with MCP: By implementing an MCP server with the official Python SDK, the agent dynamically discovers 13 typed business tools across customer lookup, order tracking, and support ticketing. The application is completely decoupled from model-specific tool wrappers.*
> 2. *Human-in-the-Loop Governance: I categorized tools into idempotent READ operations and state-mutating WRITE operations. Any write—such as drafting a ticket or modifying an order—is intercepted before reaching the database, generating a single-use cryptographic token that requires explicit user confirmation in the UI.*
> 3. *Reliability and Observability: I implemented bounded retries with exponential backoff, loop protection caps (`MAX_AGENT_STEPS = 8`), structured JSON logging with correlation IDs, Prometheus metrics, and an evaluation suite achieving 100% tool selection accuracy across 16 benchmark cases.*
> *The entire system runs on local open-weight models like Qwen or Llama via Ollama, making it reproducible and free for testing and portfolio evaluation."*

### Deep Technical Pitch (Architecture & Design Decisions)
> *"The backend is architected in distinct layers: FastAPI handles HTTP validation and rate limiting; the Agent orchestrator manages an iterative reasoning loop; the LLM Provider interface abstracts local Ollama inference from mock providers used in CI; the MCP client interacts with an official MCP server; and SQLAlchemy ORM handles parameterized data access against SQLite with Alembic migrations.*
> *Crucially, we do not allow the LLM to generate raw SQL. Instead, all database interactions occur through Pydantic-validated service contracts. This eliminates SQL injection and hallucinations while giving the model clean JSON schemas to reason over. Observability is built-in with Prometheus counters and histograms tracking token latency and tool duration, and the UI exposes safe execution traces so operators can verify every step taken by the agent."*

---

## 2. 25 Key Interview Questions & Answers

### Architecture & Technology Choices

#### 1. Why FastAPI?
**Answer:** FastAPI provides native asynchronous concurrency (`async/await`), automatic OpenAPI documentation generation (`/docs`), and deep integration with Pydantic for high-performance request validation and serialization. Its dependency injection system cleanly isolates database sessions, services, and authentication principals.

#### 2. Why SQLite for this project?
**Answer:** SQLite requires zero infrastructure setup, zero network overhead, and zero operational cost, making it ideal for a reproducible local portfolio project. Because we use SQLAlchemy ORM with standard relational patterns and Alembic migrations, switching to PostgreSQL in production only requires altering the connection string (`postgresql+asyncpg://...`) and setting a connection pool.

#### 3. Why Model Context Protocol (MCP) instead of OpenAI function calling?
**Answer:** Traditional function calling couples the application to a specific vendor's JSON format. MCP standardizes tool definitions, schemas, and resource discovery as an open protocol. Tools written once for our MCP server can be consumed by our custom agent, Claude Desktop, Antigravity IDE, or any other MCP-compliant client without code modification.

#### 4. Why Ollama?
**Answer:** Ollama allows running high-quality open-weight models (like Qwen, Llama 3, Mistral) locally on CPU or GPU over an OpenAI-compatible REST API. This ensures data privacy, zero API costs, and freedom from third-party rate limits or cloud service deprecations.

#### 5. Why not let the LLM generate and run raw SQL queries directly?
**Answer:** Allowing an LLM to generate raw SQL creates critical vulnerabilities:
1. **Security**: Susceptible to SQL injection via adversarial prompt injection.
2. **Schema Hallucination**: Models frequently invent table names, wrong column names, or invalid join clauses.
3. **Performance & Stability**: An unconstrained LLM can execute unindexed full-table scans, infinite loops, or destructive `DROP/DELETE` statements.
Exposing discrete, validated MCP tools ensures all database operations are safe, parameterized, and business-rule validated.

---

### Agent Design & Guardrails

#### 6. What is tool calling and how does the model know when to invoke a tool?
**Answer:** The LLM is provided with a system prompt and a list of tool definitions with descriptions and JSON schema parameter definitions. During generation, the model predicts whether the context requires external data. If it does, instead of emitting user-facing text, it outputs a structured payload specifying the tool name and arguments.

#### 7. How do you prevent hallucination?
**Answer:** We prevent hallucination using a three-tiered approach:
1. **Strict System Prompt Grounding**: System instructions explicitly mandate that factual business information must only come from tool results.
2. **No Fallback Guessing**: If a tool returns `None` or `Not Found`, the agent is instructed to state that the entity does not exist rather than inventing data.
3. **Execution Trace Verification**: Every tool invocation is logged in the response trace, ensuring complete data provenance.

#### 8. How do you prevent infinite loops in the agent?
**Answer:** We enforce a hard limit (`MAX_AGENT_STEPS = 8`). If the model enters a repetitive tool-calling cycle, the loop terminates deterministically, returns an error status code, increments the `agent_step_limit_exceeded_total` metric, and informs the user.

#### 9. How do you secure write operations?
**Answer:** All tools are categorized into READ and WRITE operations. When an agent attempts to execute a WRITE tool (like creating a ticket or updating an order), execution is intercepted. A one-time, cryptographically secure confirmation token with a 10-minute expiration is created. The tool is only executed once the user confirms the action via an authenticated POST request.

#### 10. What happens if a tool returns an error or invalid arguments?
**Answer:** Tool execution errors are caught, sanitized into a structured error dictionary (`{"error": "...", "code": "..."}`), and fed back to the LLM as a tool-result message. This gives the model an opportunity to self-correct (for example, re-formatting an argument) without crashing the server or leaking raw database stack traces.

---

### Observability & Security

#### 11. How is observability implemented?
**Answer:**
1. **Correlation IDs**: Every incoming request receives a UUID `request_id` and `execution_id`.
2. **Structured JSON Logging**: Logs are emitted as machine-readable JSON containing timestamp, log level, execution ID, event name, duration, and status.
3. **Prometheus Metrics**: Exposes HTTP request counts, agent loop duration, LLM inference latency, tool execution timing, and error counters at `/metrics`.

#### 12. How is authentication and authorization handled?
**Answer:** We implement Bearer token authentication via HTTP headers (`Authorization: Bearer <token>`). Tokens map to `UserPrincipal` objects with role-based permissions (`USER` vs `ADMIN`). Standard operations require `USER`, while sensitive operations require `ADMIN` or human confirmation.

#### 13. How does the rate limiter work?
**Answer:** We implemented an in-memory sliding-window rate limiter tracking requests per client IP over a 60-second window. If a client exceeds 30 requests/minute, the API responds with HTTP 429 Too Many Requests.

---

### Scaling & Production Evolution

#### 14. How would you scale this to 1,000 concurrent users?
**Answer:**
1. **Stateless Backend**: Deploy multiple FastAPI worker instances behind a load balancer (NGINX or AWS ALB).
2. **Distributed Rate Limiting & Confirmation**: Replace in-memory dictionaries with a Redis cluster for sliding-window counters and confirmation tokens.
3. **Database Scaling**: Migrate SQLite to PostgreSQL with read replicas and PgBouncer connection pooling.
4. **LLM Inference Serving**: Host open-weight models on a dedicated vLLM or Ollama cluster with dynamic batching and GPU acceleration.

#### 15. How would you replace SQLite with PostgreSQL?
**Answer:** Because our models use standard SQLAlchemy 2.0 ORM declarations:
1. Update `DATABASE_URL` in `.env` to `postgresql+asyncpg://user:pass@host:5432/db`.
2. Add `asyncpg` / `psycopg2` to dependencies.
3. Run `alembic upgrade head` to generate all tables and indexes.

#### 16. How would you replace Ollama with a cloud provider (e.g. Anthropic/OpenAI) in production?
**Answer:** Because of our `LLMProvider` abstraction, we simply write a new provider (e.g., `AnthropicProvider(LLMProvider)`) implementing `generate()` and `generate_with_tools()`. Then, in `app/llm/factory.py`, we instantiate the new provider when `LLM_PROVIDER=anthropic`. Zero agent logic needs to be rewritten.

#### 17. How would you add Redis?
**Answer:** Redis would serve two key roles:
1. **Distributed Token & Session Store**: Storing confirmation tokens with automatic TTL expiration.
2. **Sliding Window Rate Limiter**: Implementing atomic Redis sorted set (`ZADD`, `ZREMRANGEBYSCORE`) algorithms.

#### 18. How would you introduce Kafka?
**Answer:** Kafka would decouple agent operations from asynchronous backend tasks. For example, when a support ticket or order is created, the tool would publish an event (e.g. `order.created`, `ticket.dispatched`) to a Kafka topic. Background consumer microservices (email notifications, ERP synchronization) would consume the stream without blocking the user conversation.

#### 19. What happens if the LLM provider goes down?
**Answer:** The `/ready` health check endpoint queries the LLM provider. If unreachable, the system enters a graceful degraded mode: standard CRUD REST APIs (customers, orders, analytics) continue working normally, while the `/api/v1/agent/chat` endpoint returns a clear 503 Service Unavailable explaining that the AI copilot is temporarily offline.

#### 20. How are retries handled?
**Answer:** The `OllamaProvider` implements bounded exponential backoff retries (maximum 2 retries) for transient HTTP network or timeout failures. Retries are strictly avoided on client validation errors (HTTP 4xx) or stateful write operations to prevent duplicate mutations.

---

### Evaluation & Testing

#### 21. How do you evaluate an AI agent deterministically?
**Answer:** We built an evaluation framework (`evaluation/runner.py`) using 16 benchmark cases defined in YAML. The runner measures:
1. **Tool Selection Accuracy**: Did the model pick the exact expected tool?
2. **Argument Extraction Precision**: Were required IDs and filters correctly parsed?
3. **Confirmation Compliance**: Did write operations pause for human approval?
4. **Anti-Hallucination Rate**: Did the agent correctly report missing entities instead of fabricating records?

#### 22. Why separate unit tests from agent evaluation tests?
**Answer:** Unit tests must be fast, deterministic, and runnable in CI without network dependencies or local GPU/CPU hardware. Integration tests verify database integrity using an in-memory SQLite database and a mock LLM. Agent evaluation tests benchmark the actual LLM's reasoning quality.

#### 23. What is the current test coverage?
**Answer:** Over 85% test coverage across 52 unit and integration tests, verified with `pytest-cov`.

#### 24. How do you prevent prompt injection?
**Answer:**
1. System prompt separation: System rules are isolated in the system prompt role and never mixed with untrusted user input.
2. Tool argument validation: Every argument passed to a tool is parsed and validated by strict Pydantic schemas.
3. Consequential actions require explicit human confirmation tokens that cannot be forged by user prompts.

#### 25. How would you improve tool selection accuracy if the number of tools grew to 100+?
**Answer:** Passing 100+ tools directly to an LLM context window causes context bloat, increased latency, and degraded tool selection accuracy. To scale to hundreds of tools, I would implement **Semantic Tool Retrieval**: embed tool descriptions into a vector space, perform a cosine similarity search on the user's query, and only pass the top 5–10 most relevant tool schemas to the model.
