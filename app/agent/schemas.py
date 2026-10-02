"""Agent request, response, and observability execution trace schemas."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    COMPLETED = "COMPLETED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMATION_REJECTED = "CONFIRMATION_REJECTED"
    STEP_LIMIT_EXCEEDED = "STEP_LIMIT_EXCEEDED"
    FAILED = "FAILED"


class AgentRequest(BaseModel):
    message: Optional[str] = Field(default=None, description="User prompt or instruction")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID")
    confirmation_id: Optional[str] = Field(
        default=None, description="ID of pending confirmation action"
    )
    confirmed: Optional[bool] = Field(
        default=None, description="User confirmation decision (true=approve, false=cancel)"
    )


class ToolTraceEntry(BaseModel):
    step: int
    tool: str
    arguments: Dict[str, Any]
    duration_ms: float
    status: str
    result_summary: str


class ConfirmationRequest(BaseModel):
    confirmation_id: str
    tool_name: str
    operation: str
    parameters: Dict[str, Any]
    prompt_message: str


class AgentResponse(BaseModel):
    request_id: str
    execution_id: str
    status: AgentStatus
    message: str
    tool_trace: List[ToolTraceEntry] = []
    confirmation_request: Optional[ConfirmationRequest] = None
    model: str
    total_duration_ms: float
