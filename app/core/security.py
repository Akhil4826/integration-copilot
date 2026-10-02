"""Authentication, Authorization, and In-Memory Rate Limiting."""

import time
from collections import defaultdict
from typing import Optional

from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.errors import AuthenticationException, AuthorizationException, RateLimitException

settings = get_settings()
security_bearer = HTTPBearer(auto_error=False)


class UserPrincipal:
    """Authenticated caller representation."""

    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"


# In-memory sliding window rate limiter: client_id -> list of request timestamps
_rate_limit_history: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(client_identifier: str, limit_per_minute: int = 30) -> None:
    """Enforce in-memory sliding window rate limiting."""
    now = time.time()
    window_start = now - 60.0

    # Prune timestamps older than 60s
    timestamps = [t for t in _rate_limit_history[client_identifier] if t > window_start]
    if len(timestamps) >= limit_per_minute:
        _rate_limit_history[client_identifier] = timestamps
        raise RateLimitException(
            f"Rate limit of {limit_per_minute} requests/minute exceeded for '{client_identifier}'."
        )

    timestamps.append(now)
    _rate_limit_history[client_identifier] = timestamps


def reset_rate_limits() -> None:
    """Utility to clear rate limit state (useful in testing)."""
    _rate_limit_history.clear()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> UserPrincipal:
    """Authenticate Bearer token and return UserPrincipal.

    Tokens:
    - settings.api_auth_token  -> Role: USER
    - settings.admin_auth_token -> Role: ADMIN
    """
    # Rate limit by client IP before verifying auth
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(client_ip, limit_per_minute=settings.rate_limit_per_minute)

    if not credentials or not credentials.credentials:
        raise AuthenticationException("Authorization header with Bearer token is required")

    token = credentials.credentials
    if token == settings.admin_auth_token:
        return UserPrincipal(username="admin_user", role="ADMIN")
    elif token == settings.api_auth_token:
        return UserPrincipal(username="standard_user", role="USER")
    else:
        raise AuthenticationException("Invalid Bearer authentication token")


async def require_admin(
    current_user: UserPrincipal = Security(get_current_user),
) -> UserPrincipal:
    """Require ADMIN role for privileged operations."""
    if not current_user.is_admin:
        raise AuthorizationException("Admin role required for this operation")
    return current_user
