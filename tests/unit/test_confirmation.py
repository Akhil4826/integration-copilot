"""Unit tests for Confirmation Manager state and replay protection."""

import pytest

from app.agent.confirmation import ConfirmationManager
from app.core.errors import ValidationException


class TestConfirmationManager:
    def test_create_and_resolve_confirmation(self):
        cm = ConfirmationManager()
        conf = cm.create_pending_confirmation(
            tool_name="create_support_ticket",
            arguments={
                "customer_id": "CUST-1004",
                "title": "Test Title",
                "description": "Test Desc",
            },
            user_request="Create ticket for CUST-1004",
        )
        assert conf.confirmation_id
        assert conf.tool_name == "create_support_ticket"
        assert "CUST-1004" in conf.prompt_message

        # Resolve confirmation
        action = cm.resolve_confirmation(conf.confirmation_id, confirmed=True)
        assert action is not None
        assert action.tool_name == "create_support_ticket"
        assert action.arguments["customer_id"] == "CUST-1004"

        # Replay attack protection: resolving again must raise ValidationException
        with pytest.raises(ValidationException):
            cm.resolve_confirmation(conf.confirmation_id, confirmed=True)

    def test_reject_confirmation(self):
        cm = ConfirmationManager()
        conf = cm.create_pending_confirmation(
            tool_name="create_order",
            arguments={"customer_id": "CUST-1001", "product_id": "PROD-1001"},
            user_request="Place order",
        )
        # User rejects
        action = cm.resolve_confirmation(conf.confirmation_id, confirmed=False)
        assert action is None

        # Confirming after rejection must fail
        with pytest.raises(ValidationException):
            cm.resolve_confirmation(conf.confirmation_id, confirmed=True)
