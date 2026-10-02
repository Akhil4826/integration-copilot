"""Confirmation manager enforcing backend state validation for destructive/write operations."""

import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.agent.schemas import ConfirmationRequest
from app.core.errors import ValidationException


class PendingAction(BaseModel):
    confirmation_id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_request: str
    conversation_history: List[Dict[str, Any]] = []
    created_at: float = Field(default_factory=time.time)
    expires_at: float = Field(default_factory=lambda: time.time() + 900)  # 15 minutes expiry


class ConfirmationManager:
    """Stores and validates pending confirmations in memory."""

    def __init__(self):
        self._pending: Dict[str, PendingAction] = {}

    def create_pending_confirmation(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_request: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> ConfirmationRequest:
        conf_id = str(uuid.uuid4())
        action = PendingAction(
            confirmation_id=conf_id,
            tool_name=tool_name,
            arguments=arguments,
            user_request=user_request,
            conversation_history=conversation_history or [],
        )
        self._pending[conf_id] = action

        # Create human-readable operation summary
        if tool_name == "create_support_ticket":
            op_desc = f"Create a {arguments.get('priority', 'MEDIUM')} priority support ticket for customer '{arguments.get('customer_id')}'"
            order_line = (
                f"• Order ID: {arguments.get('order_id')}\n" if arguments.get("order_id") else ""
            )
            prompt = (
                f"I am ready to create a support ticket with the following details:\n"
                f"• Customer: {arguments.get('customer_id')}\n"
                f"• Priority: {arguments.get('priority', 'MEDIUM')}\n"
                f"• Title: {arguments.get('title')}\n"
                f"• Description: {arguments.get('description')}\n"
                f"{order_line}\n"
                f"Do you want me to proceed and create this ticket?"
            )
        elif tool_name == "create_order":
            op_desc = f"Place new order for customer '{arguments.get('customer_id')}' (Product: {arguments.get('product_id')}, Qty: {arguments.get('quantity', 1)})"
            prompt = (
                f"I am ready to place the following order:\n"
                f"• Customer: {arguments.get('customer_id')}\n"
                f"• Product: {arguments.get('product_id')}\n"
                f"• Quantity: {arguments.get('quantity', 1)}\n\n"
                f"Do you confirm this order placement?"
            )
        elif tool_name == "update_order_status":
            op_desc = (
                f"Update order '{arguments.get('order_id')}' status to '{arguments.get('status')}'"
            )
            prompt = f"Are you sure you want to update order '{arguments.get('order_id')}' status to '{arguments.get('status')}'?"
        elif tool_name == "update_support_ticket":
            op_desc = f"Update support ticket '{arguments.get('ticket_id')}'"
            prompt = (
                f"Are you sure you want to update support ticket '{arguments.get('ticket_id')}'?"
            )
        else:
            op_desc = f"Execute write operation '{tool_name}'"
            prompt = f"Do you confirm execution of '{tool_name}' with arguments: {arguments}?"

        return ConfirmationRequest(
            confirmation_id=conf_id,
            tool_name=tool_name,
            operation=op_desc,
            parameters=arguments,
            prompt_message=prompt,
        )

    def resolve_confirmation(
        self, confirmation_id: str, confirmed: bool
    ) -> Optional[PendingAction]:
        """Validate and resolve pending action.

        Removes action from pending store to prevent replay attacks.
        """
        action = self._pending.pop(confirmation_id, None)
        if not action:
            raise ValidationException(
                f"Confirmation ID '{confirmation_id}' is invalid or has expired."
            )

        if time.time() > action.expires_at:
            raise ValidationException(
                f"Confirmation ID '{confirmation_id}' has expired. Please re-initiate the request."
            )

        if not confirmed:
            return None

        return action


confirmation_manager = ConfirmationManager()
