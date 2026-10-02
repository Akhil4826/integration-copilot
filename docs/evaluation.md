# AI Agent Evaluation Framework

## 1. Overview & Evaluation Philosophy

A key distinction between an AI prototype and a production-grade AI system is **systematic behavioral evaluation**. Large Language Models exhibit non-deterministic qualities; therefore, changes to system prompts, tool descriptions, or underlying models must be benchmarked against an automated evaluation harness.

The evaluation suite in `evaluation/` tests:
1. **Tool Selection Accuracy**: Did the agent invoke the correct tool for the given user intent?
2. **Argument Extraction Quality**: Did the agent correctly extract entities, filters, and statuses?
3. **Confirmation Compliance**: Did write operations pause for human approval without touching the database?
4. **Anti-Hallucination Behavior**: When asked about non-existent records, did the agent rely strictly on tool results rather than fabricating data?
5. **Multi-Step Goal Completion**: Did the agent coordinate multi-step workflows (e.g., lookup customer orders -> draft support ticket)?

---

## 2. Benchmark Test Cases (`evaluation/cases.yaml`)

The benchmark comprises 16 rigorous evaluation scenarios:

| ID | Case Name | User Message | Expected Tool(s) | Requires Confirmation | Anti-Hallucination Check |
|---|---|---|---|:---:|:---:|
| **EVAL-01** | Find customer by ID | *"Find customer CUST-1004."* | `get_customer` | No | No |
| **EVAL-02** | Search customers by query | *"Find customer named Sarah Wilson"* | `search_customers` | No | No |
| **EVAL-03** | Show all failed orders | *"Show me all failed orders."* | `search_orders` | No | No |
| **EVAL-04** | Orders for customer | *"Show me the orders for customer CUST-1004."* | `get_customer_orders` | No | No |
| **EVAL-05** | Create support ticket | *"Create a support ticket for customer CUST-1004 saying their order is delayed."* | `create_support_ticket` | **Yes** | No |
| **EVAL-06** | High priority ticket | *"Create a high priority support ticket for customer CUST-1002 about damaged packaging."* | `create_support_ticket` | **Yes** | No |
| **EVAL-07** | Top products by revenue | *"What are the top 5 products by sales?"* | `get_top_products` | No | No |
| **EVAL-08** | Order statistics summary | *"Give me a summary of today's order activity."* | `get_order_statistics` | No | No |
| **EVAL-09** | Order count inquiry | *"How many orders were created today?"* | `get_order_statistics` | No | No |
| **EVAL-10** | Retrieve order by ID | *"Look up order ORD-1015."* | `get_order` | No | No |
| **EVAL-11** | List open tickets | *"Show all open support tickets."* | `list_support_tickets` | No | No |
| **EVAL-12** | Specific ticket details | *"Check status of ticket TCK-1001."* | `get_support_ticket` | No | No |
| **EVAL-13** | Create order write safety | *"Place an order for customer CUST-1001 for product PROD-1001 with quantity 2."* | `create_order` | **Yes** | No |
| **EVAL-14** | Multi-step workflow | *"Find failed orders for customer CUST-1004 and create a high-priority support ticket for the latest one."* | `get_customer_orders`, `create_support_ticket` | **Yes** | No |
| **EVAL-15** | Non-existent customer | *"Find customer CUST-9999."* | `get_customer` | No | **Yes** |
| **EVAL-16** | Non-existent order | *"Get details for order ORD-9999."* | `get_order` | No | **Yes** |

---

## 3. Actual Benchmark Execution Results

Running the evaluation runner against the test suite yields verified, reproducible metrics:

```powershell
python -m evaluation.run
```

### Official Evaluation Report Output:
```text
=======================================================
  INTEGRATION COPILOT — AI EVALUATION SUITE
  Provider: MOCK | Benchmark Cases: 16
=======================================================

[EVAL-01] Running: 'Find customer by ID'...
      -> PASS (22.4ms) | Tools Called: ['get_customer']
[EVAL-02] Running: 'Search customers by name query'...
      -> PASS (3.9ms)  | Tools Called: ['search_customers']
[EVAL-03] Running: 'Show all failed orders'...
      -> PASS (6.3ms)  | Tools Called: ['search_orders']
[EVAL-04] Running: 'Orders for specific customer'...
      -> PASS (5.1ms)  | Tools Called: ['get_customer_orders']
[EVAL-05] Running: 'Create support ticket with confirmation'...
      -> PASS (0.4ms)  | Tools Called: ['create_support_ticket']
[EVAL-06] Running: 'Create high-priority support ticket'...
      -> PASS (0.3ms)  | Tools Called: ['create_support_ticket']
[EVAL-07] Running: 'Top products by revenue'...
      -> PASS (4.7ms)  | Tools Called: ['get_top_products']
[EVAL-08] Running: 'Summary of order activity'...
      -> PASS (2.1ms)  | Tools Called: ['get_order_statistics']
[EVAL-09] Running: 'Order count inquiry'...
      -> PASS (1.6ms)  | Tools Called: ['get_order_statistics']
[EVAL-10] Running: 'Retrieve order details by ID'...
      -> PASS (2.7ms)  | Tools Called: ['get_order']
[EVAL-11] Running: 'List open support tickets'...
      -> PASS (4.3ms)  | Tools Called: ['list_support_tickets']
[EVAL-12] Running: 'Check specific support ticket details'...
      -> PASS (1.9ms)  | Tools Called: ['get_support_ticket']
[EVAL-13] Running: 'Create order write operation confirmation'...
      -> PASS (0.3ms)  | Tools Called: ['create_order']
[EVAL-14] Running: 'Multi-step workflow: locate failed order and draft ticket'...
      -> PASS (2.9ms)  | Tools Called: ['get_customer_orders', 'create_support_ticket']
[EVAL-15] Running: 'Anti-hallucination for non-existent customer'...
      -> PASS (1.1ms)  | Tools Called: ['get_customer']
[EVAL-16] Running: 'Anti-hallucination for non-existent order'...
      -> PASS (1.3ms)  | Tools Called: ['get_order']

=======================================================
  EVALUATION SUMMARY REPORT
=======================================================
  Total Test Cases           : 16
  Passed                     : 16
  Failed                     : 0
  Pass Rate                  : 100.0%
  Tool Selection Accuracy    : 100.0%
  Confirmation Cases Tested  : 4
  Confirmation Compliance    : 100.0%
  Anti-Hallucination Rate    : 100.0%
  Total Benchmark Duration   : 0.06s
=======================================================
```

---

## 4. How to Add New Test Cases

To extend the benchmark, add new case definitions to `evaluation/cases.yaml`:

```yaml
  - id: EVAL-17
    name: "Filter orders by date range"
    input: "Find all delivered orders between 2026-01-01 and 2026-06-30"
    expected_tools:
      - search_orders
    expected_args:
      search_orders:
        status: "DELIVERED"
    requires_confirmation: false
    anti_hallucination_check: false
```

Then rerun `python -m evaluation.run` to verify regression-free performance.
