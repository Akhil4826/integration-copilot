"""Agent Planner orchestrating the multi-step LLM-Tool reasoning loop."""

import json
import time
from typing import Any, Dict, List, Optional

from app.agent.confirmation import confirmation_manager
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.schemas import (
    AgentResponse,
    AgentStatus,
    ConfirmationRequest,
    ToolTraceEntry,
)
from app.agent.tool_executor import ToolExecutor
from app.core.config import get_settings
from app.core.logging import logger
from app.core.metrics import (
    AGENT_STEP_LIMIT_EXCEEDED_TOTAL,
    CONFIRMATION_REQUESTS_TOTAL,
)
from app.llm.base import LLMMessage, LLMProvider, LLMResponse

settings = get_settings()


class AgentPlanner:
    """Coordinates LLM reasoning, MCP tool discovery, multi-step loops, and confirmation gates."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_executor: Optional[ToolExecutor] = None,
        max_steps: int = 8,
    ):
        self.llm = llm_provider
        self.executor = tool_executor or ToolExecutor()
        self.max_steps = max_steps

    async def plan_and_execute(
        self,
        user_message: str,
        request_id: str,
        execution_id: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentResponse:
        start_time = time.perf_counter()
        tool_traces: List[ToolTraceEntry] = []
        seen_tool_calls: set = set()

        # 1. Fetch available MCP tools
        tool_defs = await self.executor.mcp_client.get_tool_definitions_for_llm()

        # 2. Build initial message list
        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=AGENT_SYSTEM_PROMPT),
        ]

        if conversation_history:
            for item in conversation_history:
                messages.append(LLMMessage(**item))

        messages.append(LLMMessage(role="user", content=user_message))

        step = 0
        final_answer = ""
        current_status = AgentStatus.COMPLETED
        pending_conf: Optional[ConfirmationRequest] = None

        logger.info(
            f"Starting agent planning loop for user message: '{user_message}'",
            extra={
                "event": "agent_start",
                "request_id": request_id,
                "execution_id": execution_id,
                "extra_data": {"user_message": user_message},
            },
        )

        while step < self.max_steps:
            step += 1
            logger.info(
                f"Agent step {step}/{self.max_steps}", extra={"event": "agent_step", "step": step}
            )

            # Call LLM with tools
            llm_resp: LLMResponse = await self.llm.generate_with_tools(
                messages=messages,
                tools=tool_defs,
                temperature=0.0,
            )

            # If model didn't call any tools, we have reached the final answer
            if not llm_resp.tool_calls:
                final_answer = llm_resp.content or "I have completed processing your request."
                break

            # Execute tool calls
            for tc in llm_resp.tool_calls:
                call_signature = f"{tc.name}:{json.dumps(tc.arguments, sort_keys=True)}"

                # Loop prevention: repeated identical call
                if call_signature in seen_tool_calls:
                    logger.warning(f"Repeated tool call detected: {call_signature}. Breaking loop.")
                    messages.append(
                        LLMMessage(
                            role="tool",
                            name=tc.name,
                            tool_call_id=tc.id,
                            content=json.dumps(
                                {
                                    "error": "Repeated identical tool call disallowed to avoid infinite loops."
                                }
                            ),
                        )
                    )
                    continue

                seen_tool_calls.add(call_signature)

                # Record assistant's intent in conversation history
                messages.append(
                    LLMMessage(
                        role="assistant",
                        content=llm_resp.content,
                        tool_calls=[tc],
                    )
                )

                # Execute or check confirmation
                tool_res, trace, needs_conf = await self.executor.execute(
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    step_number=step,
                    allow_write=False,
                )

                if needs_conf:
                    # Write operation intercepted: yield confirmation request
                    CONFIRMATION_REQUESTS_TOTAL.labels(tool_name=tc.name).inc()
                    conf_req = confirmation_manager.create_pending_confirmation(
                        tool_name=tc.name,
                        arguments=tc.arguments,
                        user_request=user_message,
                        conversation_history=[m.model_dump() for m in messages],
                    )
                    pending_conf = conf_req
                    current_status = AgentStatus.AWAITING_CONFIRMATION
                    final_answer = conf_req.prompt_message

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    return AgentResponse(
                        request_id=request_id,
                        execution_id=execution_id,
                        status=current_status,
                        message=final_answer,
                        tool_trace=tool_traces,
                        confirmation_request=pending_conf,
                        model=self.llm.model,
                        total_duration_ms=round(duration_ms, 2),
                    )

                if trace:
                    tool_traces.append(trace)

                # Feed tool result back into the prompt
                output_str = json.dumps(
                    tool_res.output
                    if tool_res and tool_res.success
                    else {"error": tool_res.error if tool_res else "Unknown error"}
                )
                messages.append(
                    LLMMessage(
                        role="tool",
                        name=tc.name,
                        tool_call_id=tc.id,
                        content=output_str,
                    )
                )

        if step >= self.max_steps and not final_answer:
            AGENT_STEP_LIMIT_EXCEEDED_TOTAL.inc()
            current_status = AgentStatus.STEP_LIMIT_EXCEEDED
            final_answer = (
                f"Agent reached maximum execution step limit ({self.max_steps}) without concluding. "
                "The operation was safely halted to prevent infinite loops."
            )
            logger.warning(
                f"Agent exceeded MAX_AGENT_STEPS ({self.max_steps}) for execution {execution_id}",
                extra={"event": "step_limit_exceeded", "execution_id": execution_id},
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        return AgentResponse(
            request_id=request_id,
            execution_id=execution_id,
            status=current_status,
            message=final_answer,
            tool_trace=tool_traces,
            confirmation_request=None,
            model=self.llm.model,
            total_duration_ms=round(duration_ms, 2),
        )
