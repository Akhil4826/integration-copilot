"""Deterministic Mock LLM Provider for unit testing, CI, and local evaluation."""

import re
from typing import Any, Callable, Dict, List, Optional

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall


class MockLLMProvider(LLMProvider):
    """Deterministic LLM Provider that inspects user queries or tool results and yields
    appropriate tool calls or final responses without needing a local GPU or network server.
    """

    def __init__(self, model: str = "mock-model"):
        self.model = model
        self.custom_responder: Optional[Callable[[List[LLMMessage]], LLMResponse]] = None

    def set_custom_responder(self, fn: Callable[[List[LLMMessage]], LLMResponse]):
        self.custom_responder = fn

    async def generate(self, messages: List[LLMMessage], **kwargs: Any) -> LLMResponse:
        return await self.generate_with_tools(messages, tools=[], **kwargs)

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> LLMResponse:
        if self.custom_responder:
            return self.custom_responder(messages)

        # Inspect last message
        last_msg = messages[-1] if messages else LLMMessage(role="user", content="")

        # 1. If last message is a tool response, summarize the result!
        if last_msg.role == "tool" or (len(messages) > 1 and messages[-2].tool_calls):
            # Check if this was a multi-step sequence
            # E.g., if user asked "Find failed orders for customer CUST-1004 and create a high-priority support ticket for the latest one"
            first_user_content = next((m.content or "" for m in messages if m.role == "user"), "")
            if (
                "and create" in first_user_content.lower()
                and "ticket" in first_user_content.lower()
            ):
                # Check if we already created ticket or called search_orders
                last_tool_name = messages[-1].name if messages[-1].role == "tool" else ""
                if last_tool_name in ("get_customer_orders", "search_orders"):
                    # Step 2 of multi-step: create ticket for latest failed order
                    return LLMResponse(
                        content="I identified the latest failed order for customer CUST-1004 (ORD-1015). Now creating a support ticket.",
                        tool_calls=[
                            LLMToolCall(
                                id="call_multi_step_ticket",
                                name="create_support_ticket",
                                arguments={
                                    "customer_id": "CUST-1004",
                                    "order_id": "ORD-1015",
                                    "title": "Delivery delayed for failed order ORD-1015",
                                    "description": "Customer order ORD-1015 failed during checkout.",
                                    "priority": "HIGH",
                                },
                            )
                        ],
                        finish_reason="tool_calls",
                        model=self.model,
                    )

            # Standard final summary
            return LLMResponse(
                content=f"Based on the tool results: {last_msg.content or 'Operation completed successfully.'}",
                tool_calls=None,
                finish_reason="stop",
                model=self.model,
                duration_seconds=0.01,
            )

        # 2. Extract intent from user request
        user_text = (last_msg.content or "").lower().strip()

        # Multi-step: "Find failed orders for customer CUST-1004 and create a high-priority support ticket for the latest one."
        if (
            "failed orders for customer" in user_text or "failed order" in user_text
        ) and "create" in user_text:
            cust_match = re.search(r"cust-\d{4}", user_text, re.IGNORECASE)
            c_id = cust_match.group(0).upper() if cust_match else "CUST-1004"
            return LLMResponse(
                content="I will first retrieve the customer's orders to locate the latest failed order.",
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_multistep_1",
                        name="get_customer_orders",
                        arguments={"customer_id": c_id},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Place / Create order (Write tool requiring confirmation)
        if (
            "place an order" in user_text
            or "create an order" in user_text
            or "create order" in user_text
        ):
            cust_match = re.search(r"cust-\d{4}", user_text, re.IGNORECASE)
            prod_match = re.search(r"prod-\d{4}", user_text, re.IGNORECASE)
            qty_match = re.search(r"quantity\s+(\d+)", user_text, re.IGNORECASE)
            c_id = cust_match.group(0).upper() if cust_match else "CUST-1001"
            p_id = prod_match.group(0).upper() if prod_match else "PROD-1001"
            qty = int(qty_match.group(1)) if qty_match else 1
            return LLMResponse(
                content="Preparing to place an order for the customer.",
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_order_create",
                        name="create_order",
                        arguments={"customer_id": c_id, "product_id": p_id, "quantity": qty},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Support ticket creation (Write tool requiring confirmation)
        if (
            ("create" in user_text and "ticket" in user_text)
            or "create a support ticket" in user_text
            or "support ticket for" in user_text
        ):
            cust_match = re.search(r"cust-\d{4}", user_text, re.IGNORECASE)
            c_id = cust_match.group(0).upper() if cust_match else "CUST-1004"
            prio = (
                "HIGH"
                if "high" in user_text
                else ("CRITICAL" if "critical" in user_text else "MEDIUM")
            )
            desc = (
                "Order is delayed"
                if "delayed" in user_text
                else (
                    "Damaged packaging reported"
                    if "damaged" in user_text
                    else "Customer reported an issue"
                )
            )
            title = (
                "Order delay report"
                if "delayed" in user_text
                else (
                    "Damaged packaging issue"
                    if "damaged" in user_text
                    else "Customer support issue"
                )
            )
            return LLMResponse(
                content="Preparing to create a support ticket for the customer.",
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_ticket",
                        name="create_support_ticket",
                        arguments={
                            "customer_id": c_id,
                            "title": title,
                            "description": desc,
                            "priority": prio,
                        },
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Orders for specific customer
        if "orders for customer" in user_text or "orders for cust-" in user_text:
            cust_match = re.search(r"cust-\d{4}", user_text, re.IGNORECASE)
            c_id = cust_match.group(0).upper() if cust_match else "CUST-1004"
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_2",
                        name="get_customer_orders",
                        arguments={"customer_id": c_id},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Specific order lookup (e.g. Look up order ORD-1015)
        ord_match = re.search(r"ord-\d{4}", user_text, re.IGNORECASE)
        if ord_match and ("order" in user_text or "look up" in user_text or "details" in user_text):
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_get_order",
                        name="get_order",
                        arguments={"order_id": ord_match.group(0).upper()},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Specific ticket lookup (e.g. Check status of ticket TCK-1001)
        tck_match = re.search(r"tck-\d{4}", user_text, re.IGNORECASE)
        if tck_match:
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_get_tck",
                        name="get_support_ticket",
                        arguments={"ticket_id": tck_match.group(0).upper()},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # List support tickets (e.g. Show all open support tickets)
        if (
            "support ticket" in user_text
            or "support tickets" in user_text
            or "tickets" in user_text
        ):
            filter_stat: Optional[str] = "OPEN" if "open" in user_text else None
            filter_prio: Optional[str] = "HIGH" if "high" in user_text else None
            args: Dict[str, Any] = {}
            if filter_stat:
                args["status"] = filter_stat
            if filter_prio:
                args["priority"] = filter_prio
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_list_tck",
                        name="list_support_tickets",
                        arguments=args,
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Failed orders
        if "failed order" in user_text or "failed orders" in user_text:
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_failed",
                        name="search_orders",
                        arguments={"status": "FAILED", "limit": 10},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Find customer CUST-XXXX or search customers
        if "customer" in user_text:
            cust_match = re.search(r"cust-\d{4}", user_text, re.IGNORECASE)
            if cust_match:
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        LLMToolCall(
                            id="call_mock_1",
                            name="get_customer",
                            arguments={"customer_id": cust_match.group(0).upper()},
                        )
                    ],
                    finish_reason="tool_calls",
                    model=self.model,
                )
            else:
                # Name search
                q = user_text
                for prefix in [
                    "find customer named",
                    "find customer",
                    "search customer",
                    "search for customer",
                ]:
                    q = q.replace(prefix, "")
                clean_q = q.strip().title()
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        LLMToolCall(
                            id="call_mock_search_cust",
                            name="search_customers",
                            arguments={"query": clean_q},
                        )
                    ],
                    finish_reason="tool_calls",
                    model=self.model,
                )

        # Top products
        if "top" in user_text and "product" in user_text:
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_top_prod",
                        name="get_top_products",
                        arguments={"limit": 5},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Order statistics / today's order activity / summary
        if (
            "summary" in user_text
            or "statistics" in user_text
            or "activity" in user_text
            or "how many orders" in user_text
        ):
            return LLMResponse(
                content=None,
                tool_calls=[
                    LLMToolCall(
                        id="call_mock_stats",
                        name="get_order_statistics",
                        arguments={},
                    )
                ],
                finish_reason="tool_calls",
                model=self.model,
            )

        # Fallback conversational response
        return LLMResponse(
            content="Hello! I am your Integration Copilot. I can help look up customers, search orders, review order metrics, and manage support tickets.",
            tool_calls=None,
            finish_reason="stop",
            model=self.model,
        )

    async def health_check(self) -> bool:
        return True
