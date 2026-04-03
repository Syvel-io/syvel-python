"""Syvel — disposable email detection SDK for Python.

Quickstart::

    from syvel import Syvel

    client = Syvel(api_key="sv_...")
    result = client.check_email("user@example.com")
    if result and result.is_risky:
        raise ValueError("Disposable email not allowed")

Async usage::

    from syvel import AsyncSyvel

    async with AsyncSyvel(api_key="sv_...") as client:
        result = await client.check_email("user@example.com")

Fail-open (silent) mode::

    client = Syvel(api_key="sv_...", silent=True)
    result = client.check_email("user@example.com")
    # Returns None on any error — never blocks your signup flow
"""

from syvel._version import __version__
from syvel.async_client import AsyncSyvel
from syvel.client import Syvel
from syvel.exceptions import (
    SyvelAuthError,
    SyvelError,
    SyvelForbiddenError,
    SyvelRateLimitError,
    SyvelTimeoutError,
    SyvelValidationError,
)
from syvel.models import ApiKey, CheckResult, LogEntry, LogsPage, StatsPoint, UsageResult

__all__ = [
    "__version__",
    # Clients
    "Syvel",
    "AsyncSyvel",
    # Models
    "CheckResult",
    "UsageResult",
    "LogEntry",
    "LogsPage",
    "StatsPoint",
    "ApiKey",
    # Exceptions
    "SyvelError",
    "SyvelAuthError",
    "SyvelForbiddenError",
    "SyvelValidationError",
    "SyvelRateLimitError",
    "SyvelTimeoutError",
]
