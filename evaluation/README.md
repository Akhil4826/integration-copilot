# AI Agent Evaluation Benchmark Suite

This directory contains the automated evaluation framework for benchmarking **Integration Copilot**.

## Objectives
1. **Tool Selection Accuracy**: Measures whether the LLM selects the correct MCP tool corresponding to the user's intent.
2. **Argument Extraction Accuracy**: Verifies that entities, IDs, statuses, and numerical thresholds are correctly extracted into tool call arguments.
3. **Confirmation Compliance**: Ensures that write/destructive operations (`create_support_ticket`, `create_order`, `update_order_status`, `update_support_ticket`) are never autonomously applied without human confirmation.
4. **Anti-Hallucination & Grounding**: Verifies that when entities do not exist in the database (e.g. `CUST-9999` or `ORD-9999`), the agent accurately reports the missing status rather than hallucinating details.
5. **Multi-Step Orchestration**: Evaluates multi-step flows (e.g. locating a failed order first, then creating a support ticket).

## Running the Evaluation

To run with the local deterministic mock provider (fast, offline, reproducible):
```bash
python -m evaluation.run
```

To run against your live locally running Ollama instance (`LLM_MODEL=qwen3:4b`):
```bash
python -m evaluation.run --provider ollama
```

## Test Cases
Defined in `evaluation/cases.yaml`.
Each test case contains:
- `id`: Unique identifier (e.g. `EVAL-01`)
- `name`: Descriptive test name
- `query`: The user natural language prompt
- `category`: Category (`tool_selection`, `confirmation_compliance`, `multi_step`, `anti_hallucination`)
- `expected_tool`: Expected MCP tool to be selected
- `expected_args`: Key expected arguments
- `requires_confirmation`: Boolean flag checking confirmation state
