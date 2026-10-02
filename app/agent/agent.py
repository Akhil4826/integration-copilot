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
from app.llm.mock_provider import MockLLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider

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

    def _get_planner_for_request(self, request: AgentRequest) -> AgentPlanner:
        if not request.llm_provider or request.llm_provider == settings.llm_provider:
            return self.planner

        prov_type = request.llm_provider.lower().strip()
        if prov_type == "mock":
            return AgentPlanner(
                llm_provider=MockLLMProvider(model=request.llm_model or "deterministic-agent"),
                max_steps=settings.max_agent_steps,
            )
        elif prov_type in ("groq", "openai_compatible"):
            base_url = request.api_base or (
                "https://api.groq.com/openai/v1"
                if prov_type == "groq"
                else "https://api.openai.com/v1"
            )
            api_key = request.api_key or settings.groq_api_key
            model = request.llm_model or (
                "llama-3.3-70b-versatile" if prov_type == "groq" else "gpt-3.5-turbo"
            )
            cloud_provider = OpenAICompatibleProvider(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout_seconds=settings.llm_timeout_seconds,
                max_retries=settings.max_tool_retries,
            )
            return AgentPlanner(llm_provider=cloud_provider, max_steps=settings.max_agent_steps)
        elif prov_type == "ollama":
            base_url = request.api_base or settings.ollama_base_url
            model = request.llm_model or settings.llm_model
            ollama_provider = OllamaProvider(
                base_url=base_url,
                model=model,
                timeout_seconds=settings.llm_timeout_seconds,
                max_retries=settings.max_tool_retries,
            )
            return AgentPlanner(llm_provider=ollama_provider, max_steps=settings.max_agent_steps)
        return self.planner

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

            # Get appropriate planner (dynamic request override or default)
            planner = self._get_planner_for_request(request)

            try:
                response = await planner.plan_and_execute(
                    user_message=request.message or "",
                    request_id=request_id,
                    execution_id=execution_id,
                )
            except Exception as exc:
                # Automatic resilient fallback: if cloud provider fails,
                # seamlessly fulfill request via deterministic built-in engine
                logger.warning(
                    f"Selected LLM provider failed ({exc}). Engaging resilient fallback."
                )
                fallback_planner = AgentPlanner(
                    llm_provider=MockLLMProvider(model="resilient-copilot"),
                    max_steps=settings.max_agent_steps,
                )
                response = await fallback_planner.plan_and_execute(
                    user_message=request.message or "",
                    request_id=request_id,
                    execution_id=execution_id,
                )
                notice = f"*(Notice: External LLM error [{exc}]. Seamlessly completed via built-in resilient engine.)*\n\n"
                response.message = notice + response.message

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

        try:
            llm_resp = await self.llm.generate(messages)
            final_text = (
                llm_resp.content or f"Operation '{pending_action.tool_name}' executed successfully."
            )
        except Exception:
            final_text = f"Action confirmed: Successfully executed '{pending_action.tool_name}'."
            if tool_res and tool_res.output:
                final_text += f"\nResult: {tool_res.output}"

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
