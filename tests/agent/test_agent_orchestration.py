"""Agent orchestration, multi-step workflows, confirmation gating, and safety tests."""

import pytest

from app.agent.agent import AgentService
from app.agent.planner import AgentPlanner
from app.agent.schemas import AgentRequest, AgentStatus
from app.llm.base import LLMResponse, LLMToolCall
from app.llm.mock_provider import MockLLMProvider


class TestAgentOrchestration:
    @pytest.mark.asyncio
    async def test_agent_read_tool_flow(self, mock_llm):
        service = AgentService(llm_provider=mock_llm)
        req = AgentRequest(message="Show me all failed orders.")
        resp = await service.run(req)

        assert resp.status == AgentStatus.COMPLETED
        assert resp.request_id
        assert resp.execution_id
        assert len(resp.tool_trace) >= 1
        assert resp.tool_trace[0].tool == "search_orders"
        assert resp.tool_trace[0].status == "success"
        assert "Retrieved" in resp.tool_trace[0].result_summary

    @pytest.mark.asyncio
    async def test_agent_customer_lookup_flow(self, mock_llm):
        service = AgentService(llm_provider=mock_llm)
        req = AgentRequest(message="Find customer CUST-1004.")
        resp = await service.run(req)

        assert resp.status == AgentStatus.COMPLETED
        assert any(t.tool == "get_customer" for t in resp.tool_trace)
        assert "CUST-1004" in resp.message or any(
            "CUST-1004" in t.result_summary for t in resp.tool_trace
        )

    @pytest.mark.asyncio
    async def test_agent_write_tool_requires_confirmation(self, mock_llm):
        service = AgentService(llm_provider=mock_llm)
        req = AgentRequest(
            message="Create a support ticket for customer CUST-1004 saying their order is delayed."
        )
        resp = await service.run(req)

        # Write tool MUST be intercepted
        assert resp.status == AgentStatus.AWAITING_CONFIRMATION
        assert resp.confirmation_request is not None
        assert resp.confirmation_request.tool_name == "create_support_ticket"
        assert resp.confirmation_request.parameters["customer_id"] == "CUST-1004"
        assert "Do you want me to proceed" in resp.confirmation_request.prompt_message

        # Resolve confirmation with approval
        conf_id = resp.confirmation_request.confirmation_id
        confirm_req = AgentRequest(
            message="Confirmed",
            confirmation_id=conf_id,
            confirmed=True,
        )
        conf_resp = await service.run(confirm_req)

        assert conf_resp.status == AgentStatus.COMPLETED
        assert len(conf_resp.tool_trace) == 1
        assert conf_resp.tool_trace[0].tool == "create_support_ticket"
        assert conf_resp.tool_trace[0].status == "success"

    @pytest.mark.asyncio
    async def test_agent_write_tool_rejection(self, mock_llm):
        service = AgentService(llm_provider=mock_llm)
        req = AgentRequest(
            message="Place an order for customer CUST-1001 for product PROD-1001 with quantity 2."
        )
        resp = await service.run(req)

        assert resp.status == AgentStatus.AWAITING_CONFIRMATION
        conf_id = resp.confirmation_request.confirmation_id

        # User cancels
        reject_req = AgentRequest(
            message="Cancel",
            confirmation_id=conf_id,
            confirmed=False,
        )
        rej_resp = await service.run(reject_req)

        assert rej_resp.status == AgentStatus.CONFIRMATION_REJECTED
        assert "cancelled by user" in rej_resp.message.lower()

    @pytest.mark.asyncio
    async def test_agent_multi_step_workflow(self, mock_llm):
        service = AgentService(llm_provider=mock_llm)
        req = AgentRequest(
            message="Find failed orders for customer CUST-1004 and create a high-priority support ticket for the latest one."
        )
        resp = await service.run(req)

        # Step 1 retrieved orders, Step 2 prepared ticket and intercepted for confirmation
        assert resp.status == AgentStatus.AWAITING_CONFIRMATION
        assert len(resp.tool_trace) >= 1
        assert resp.tool_trace[0].tool == "get_customer_orders"
        assert resp.confirmation_request is not None
        assert resp.confirmation_request.tool_name == "create_support_ticket"

    @pytest.mark.asyncio
    async def test_agent_step_limit_loop_protection(self):
        # Create a mock that infinitely issues tool calls
        infinite_mock = MockLLMProvider()
        infinite_mock.set_custom_responder(
            lambda msgs: LLMResponse(
                content="Looping...",
                tool_calls=[
                    LLMToolCall(
                        id=f"loop_call_{len(msgs)}",
                        name="get_order_statistics",
                        arguments={"salt": len(msgs)},
                    )
                ],
                finish_reason="tool_calls",
                model="infinite-model",
            )
        )

        planner = AgentPlanner(llm_provider=infinite_mock, max_steps=4)
        service = AgentService(llm_provider=infinite_mock, planner=planner)

        resp = await service.run(AgentRequest(message="Trigger loop"))
        assert resp.status == AgentStatus.STEP_LIMIT_EXCEEDED
        assert "step limit (4)" in resp.message.lower()

    @pytest.mark.asyncio
    async def test_anti_hallucination_on_missing_entity(self, mock_llm):
        service = AgentService(llm_provider=mock_llm)
        req = AgentRequest(message="Find customer CUST-9999.")
        resp = await service.run(req)

        assert resp.status == AgentStatus.COMPLETED
        # Must indicate not found rather than hallucinating details
        assert "not found" in resp.message.lower() or any(
            "not found" in t.result_summary.lower() for t in resp.tool_trace
        )
