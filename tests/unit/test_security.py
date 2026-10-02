"""Unit tests for Authentication, Authorization, and Rate Limiting."""

import pytest

from app.core.config import get_settings
from app.core.errors import AuthorizationException, RateLimitException
from app.core.security import UserPrincipal, check_rate_limit, require_admin, reset_rate_limits

settings = get_settings()


class TestSecurityUnit:
    def test_user_principal_roles(self):
        user = UserPrincipal(username="standard", role="USER")
        assert not user.is_admin

        admin = UserPrincipal(username="admin", role="ADMIN")
        assert admin.is_admin

    @pytest.mark.asyncio
    async def test_require_admin_guard(self):
        admin = UserPrincipal(username="admin", role="ADMIN")
        res = await require_admin(admin)
        assert res.username == "admin"

        user = UserPrincipal(username="standard", role="USER")
        with pytest.raises(AuthorizationException) as exc:
            await require_admin(user)
        assert exc.value.status_code == 403

    def test_rate_limiting_sliding_window(self):
        reset_rate_limits()
        client_id = "test-client-123"

        # Allow 30 requests
        for _ in range(30):
            check_rate_limit(client_id, limit_per_minute=30)

        # 31st request must trigger RateLimitException
        with pytest.raises(RateLimitException) as exc:
            check_rate_limit(client_id, limit_per_minute=30)
        assert exc.value.status_code == 429
        assert "exceeded" in exc.value.message.lower()

        reset_rate_limits()
