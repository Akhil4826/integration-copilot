"""Prometheus-compatible metrics instrumentation for HTTP, Agent, LLM, and Tools."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

# HTTP Request Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Agent Execution Metrics
AGENT_REQUESTS_TOTAL = Counter(
    "agent_requests_total",
    "Total agent user requests received",
    ["status"],
)
AGENT_EXECUTION_DURATION_SECONDS = Histogram(
    "agent_execution_duration_seconds",
    "End-to-end agent execution duration in seconds",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
)
AGENT_STEP_LIMIT_EXCEEDED_TOTAL = Counter(
    "agent_step_limit_exceeded_total",
    "Total times the agent exceeded MAX_AGENT_STEPS loop limit",
)
CONFIRMATION_REQUESTS_TOTAL = Counter(
    "confirmation_requests_total",
    "Total times the agent yielded a confirmation request for a write operation",
    ["tool_name"],
)

# Tool Execution Metrics
TOOL_CALLS_TOTAL = Counter(
    "tool_calls_total",
    "Total tool calls executed",
    ["tool_name", "status"],
)
TOOL_EXECUTION_DURATION_SECONDS = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration in seconds",
    ["tool_name"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0),
)
TOOL_ERRORS_TOTAL = Counter(
    "tool_errors_total",
    "Total tool execution errors",
    ["tool_name", "error_type"],
)

# LLM Metrics
LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total requests to LLM provider",
    ["model", "status"],
)
LLM_REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "LLM provider response time in seconds",
    ["model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
)


def get_metrics_data() -> tuple[bytes, str]:
    """Generate latest metrics in Prometheus text format."""
    return generate_latest(), CONTENT_TYPE_LATEST
