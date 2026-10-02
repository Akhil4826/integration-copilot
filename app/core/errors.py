"""Centralized application exceptions and error handling structures."""

from typing import Any, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} '{identifier}' was not found",
            status_code=404,
        )


class ValidationException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details,
        )


class AuthenticationException(AppException):
    def __init__(self, message: str = "Invalid or missing authentication credentials"):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401,
        )


class AuthorizationException(AppException):
    def __init__(self, message: str = "Access forbidden: insufficient permissions"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


class RateLimitException(AppException):
    def __init__(
        self, message: str = "Rate limit exceeded. Maximum 30 requests per minute allowed."
    ):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
        )


class ToolExecutionException(AppException):
    def __init__(self, tool_name: str, message: str, details: Optional[Any] = None):
        super().__init__(
            code="TOOL_EXECUTION_ERROR",
            message=f"Error executing tool '{tool_name}': {message}",
            status_code=500,
            details=details,
        )


class ConfirmationRequiredException(AppException):
    def __init__(self, operation: str, pending_action: dict[str, Any]):
        super().__init__(
            code="CONFIRMATION_REQUIRED",
            message=f"Operation '{operation}' requires explicit user confirmation before proceeding.",
            status_code=409,
            details=pending_action,
        )
