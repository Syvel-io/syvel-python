"""Syvel exception hierarchy."""

from __future__ import annotations

from datetime import datetime


class SyvelError(Exception):
    """Base class for all Syvel SDK errors.

    Attributes:
        status_code: HTTP status code, if the error originated from an API response.
        code: Machine-readable error code string.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class SyvelAuthError(SyvelError):
    """Raised when the API key is invalid or missing (HTTP 401)."""

    def __init__(self) -> None:
        super().__init__(
            "Invalid or missing Syvel API key. "
            "Check your api_key and visit https://www.syvel.io/dashboard to generate one.",
            status_code=401,
            code="UNAUTHORIZED",
        )


class SyvelForbiddenError(SyvelError):
    """Raised when the request origin is not authorised for this API key (HTTP 403)."""

    def __init__(self) -> None:
        super().__init__(
            "This origin is not authorised for this API key. "
            "Add it in your Syvel dashboard under project settings.",
            status_code=403,
            code="FORBIDDEN",
        )


class SyvelValidationError(SyvelError):
    """Raised when the email or domain format is invalid (HTTP 422)."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            detail or "Invalid email or domain format.",
            status_code=422,
            code="VALIDATION_ERROR",
        )


class SyvelRateLimitError(SyvelError):
    """Raised when the monthly request quota has been exceeded (HTTP 429).

    Attributes:
        reset_at: UTC datetime at which the quota resets, or ``None`` if not provided
            by the API.
    """

    def __init__(self, reset_at: datetime | None = None) -> None:
        super().__init__(
            "Syvel monthly quota exceeded. "
            "Upgrade your plan at https://www.syvel.io/dashboard.",
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
        )
        self.reset_at = reset_at


class SyvelTimeoutError(SyvelError):
    """Raised when a request exceeds the configured timeout.

    Always fail open: catch this error and allow the user through rather than
    blocking on a third-party service failure.
    """

    def __init__(self, timeout_s: float) -> None:
        super().__init__(
            f"Syvel request timed out after {timeout_s}s.",
            code="TIMEOUT",
        )
        self.timeout_s = timeout_s
