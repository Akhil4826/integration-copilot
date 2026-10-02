"""Agent service coordinating requests, execution IDs, confirmation resolution, and metrics."""

import time
import uuid
from typing import Optional

from app.agent.confirmation import confirmation_manager
from app.agent.planner import AgentPlanner
from app.agent.schemas import AgentRequest, AgentResponse, AgentStatus
from app.core.config import get_settings
from app.core.logging import current_execution_id, current_request_id, logger
from app.core.metrics import (
    AGENT_EXECUTION_DURATION_SECONDS,
    AGENT_REQUESTS_TOTAL,
)
from app.llm.base import LLMMessage, LLMProvider
from app.llm.factory import get_llm_provider

settings = get_settings()


class AgentService:
    """Entry point for handling user chat interactions with the business assistant."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        planner: Optional[AgentPlanner] = None,
    ):
        self.llm = llm_provider or get_llm_provider()
        self.planner = planner or AgentPlanner(
            llm_provider=self.llm,
            max_steps=settings.max_agent_steps,
        )

    async def run(self, request: AgentRequest) -> AgentResponse:
        request_id = str(uuid.uuid4())
        execution_id = str(uuid.uuid4())
        token_req = current_request_id.set(request_id)
        token_exec = current_execution_id.set(execution_id)

        start_time = time.perf_counter()
        AGENT_REQUESTS_TOTAL.labels(status="received").inc()

        try:
            # Check if this is a response to a pending confirmation
            if request.confirmation_id:
                return await self._handle_confirmation_resolution(
                    request=request,
                    request_id=request_id,
                    execution_id=execution_id,
                    start_time=start_time,
                )

            # Normal autonomous planning and execution
            response = await self.planner.plan_and_execute(
                user_message=request.message or "",
                request_id=request_id,
                execution_id=execution_id,
            )

            duration_sec = time.perf_counter() - start_time
            AGENT_EXECUTION_DURATION_SECONDS.observe(duration_sec)
            AGENT_REQUESTS_TOTAL.labels(status=response.status.value).inc()

            return response

        except Exception as exc:
            duration_sec = time.perf_counter() - start_time
            AGENT_EXECUTION_DURATION_SECONDS.observe(duration_sec)
            AGENT_REQUESTS_TOTAL.labels(status="error").inc()
            logger.error(
                f"Unhandled agent error: {str(exc)}",
                extra={"event": "agent_error", "execution_id": execution_id},
                exc_info=True,
            )
            return AgentResponse(
                request_id=request_id,
                execution_id=execution_id,
                status=AgentStatus.FAILED,
                message=f"An error occurred while processing your request: {str(exc)}",
                tool_trace=[],
                model=self.llm.model,
                total_duration_ms=round(duration_sec * 1000, 2),
            )

        finally:
            current_request_id.reset(token_req)
            current_execution_id.reset(token_exec)

    async def _handle_confirmation_resolution(
        self,
        request: AgentRequest,
        request_id: str,
        execution_id: str,
        start_time: float,
    ) -> AgentResponse:
        """Resolve a previously pending confirmation request."""
        conf_id = request.confirmation_id or ""
        confirmed = bool(request.confirmed)

        pending_action = confirmation_manager.resolve_confirmation(conf_id, confirmed=confirmed)

        if not confirmed or not pending_action:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return AgentResponse(
                request_id=request_id,
                execution_id=execution_id,
                status=AgentStatus.CONFIRMATION_REJECTED,
                message="Operation cancelled by user. No database changes were applied.",
                tool_trace=[],
                model=self.llm.model,
                total_duration_ms=round(duration_ms, 2),
            )

        # User approved: execute the write tool now with allow_write=True
        tool_res, trace, _ = await self.planner.executor.execute(
            tool_name=pending_action.tool_name,
            arguments=pending_action.arguments,
            step_number=1,
            allow_write=True,
        )

        tool_traces = [trace] if trace else []

        # Generate polite final confirmation response with LLM
        messages = [
            LLMMessage(
                role="system",
                content="You are Integration Copilot. Summarize the confirmed operation factually.",
            ),
            LLMMessage(role="user", content=pending_action.user_request),
            LLMMessage(
                role="tool",
                name=pending_action.tool_name,
                content=str(tool_res.output if tool_res else {}),
            ),
        ]

        llm_resp = await self.llm.generate(messages)
        final_text = (
            llm_resp.content or f"Operation '{pending_action.tool_name}' executed successfully."
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        return AgentResponse(
            request_id=request_id,
            execution_id=execution_id,
            status=AgentStatus.COMPLETED,
            message=final_text,
            tool_trace=tool_traces,
            model=self.llm.model,
            total_duration_ms=round(duration_ms, 2),
        )
