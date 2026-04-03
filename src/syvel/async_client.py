"""Asynchronous Syvel client."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, cast

import httpx

from syvel._http import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    _encode_target,
    _make_headers,
    _parse_response,
    _validate_email,
)
from syvel.exceptions import SyvelError, SyvelTimeoutError
from syvel.models import ApiKey, CheckResult, LogsPage, StatsPoint, UsageResult

if TYPE_CHECKING:
    pass


class AsyncSyvel:
    """Asynchronous Syvel client.

    Wraps the Syvel API using ``httpx.AsyncClient`` for async/await usage.
    Must be used as an async context manager or closed explicitly with
    :meth:`aclose`:

    .. code-block:: python

        async with AsyncSyvel(api_key="sv_...") as client:
            result = await client.check_email("user@example.com")
            if result and result.is_risky:
                raise ValueError("Disposable email not allowed")

    This client is ideal for FastAPI, async Django, Starlette, and any other
    ``asyncio``-based framework.

    Args:
        api_key: Your Syvel API key (format: ``sv_...``). Generate one at
            https://www.syvel.io/dashboard.
        base_url: API base URL. Defaults to ``https://api.syvel.io``.
        timeout: Request timeout in seconds. Defaults to ``3.0``.
            Always fail open when you catch :class:`~syvel.exceptions.SyvelTimeoutError`.
        silent: When ``True``, all errors are suppressed and methods return ``None``
            instead of raising. Useful for non-critical checks where you prefer to
            accept users rather than block on a third-party failure.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        silent: bool = False,
    ) -> None:
        if not api_key:
            raise ValueError(
                "api_key is required. Generate one at https://www.syvel.io/dashboard."
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._silent = silent
        self._headers = _make_headers(api_key)
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
            follow_redirects=False,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def check(self, domain: str) -> CheckResult | None:
        """Check a domain for disposable-email risk.

        Use :meth:`check_email` when you have a full email address — it enables
        local-part analysis (role account detection, random pattern scoring).

        Args:
            domain: Bare domain to check (e.g. ``"yopmail.com"``).

        Returns:
            A :class:`~syvel.models.CheckResult`, or ``None`` if ``silent=True``
            and an error occurred.

        Raises:
            :class:`~syvel.exceptions.SyvelAuthError`: Invalid or missing API key.
            :class:`~syvel.exceptions.SyvelRateLimitError`: Monthly quota exceeded.
            :class:`~syvel.exceptions.SyvelTimeoutError`: Request timed out.
            :class:`~syvel.exceptions.SyvelError`: Any other API error.
        """
        data = await self._request("GET", f"/v1/check/{_encode_target(domain)}")
        if data is None:
            return None
        return CheckResult.from_dict(data)

    async def check_email(self, email: str) -> CheckResult | None:
        """Check a full email address for disposable-email risk.

        Passes the complete address to the API (including the local part) to
        enable role-account detection (e.g. ``admin@``, ``info@``) and random
        pattern analysis.

        Args:
            email: Full email address to check (e.g. ``"user@example.com"``).

        Returns:
            A :class:`~syvel.models.CheckResult`, or ``None`` if ``silent=True``
            and an error occurred.

        Raises:
            :class:`~syvel.exceptions.SyvelError`: If *email* does not contain ``@``
                and ``silent=False``.
            :class:`~syvel.exceptions.SyvelAuthError`: Invalid or missing API key.
            :class:`~syvel.exceptions.SyvelRateLimitError`: Monthly quota exceeded.
            :class:`~syvel.exceptions.SyvelTimeoutError`: Request timed out.
        """
        if not _validate_email(email, silent=self._silent):
            return None
        return await self.check(email)

    async def usage(self) -> UsageResult | None:
        """Retrieve the current monthly quota and usage statistics.

        Returns:
            A :class:`~syvel.models.UsageResult`, or ``None`` if ``silent=True``
            and an error occurred.
        """
        data = await self._request("GET", "/v1/usage")
        if data is None:
            return None
        return UsageResult.from_dict(data)

    async def logs(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> LogsPage | None:
        """Retrieve a paginated page of request logs.

        Args:
            cursor: Pagination cursor from a previous :class:`~syvel.models.LogsPage`
                response. Omit to start from the most recent entries.
            limit: Maximum number of entries to return per page.

        Returns:
            A :class:`~syvel.models.LogsPage`, or ``None`` if ``silent=True``
            and an error occurred.
        """
        params: dict[str, str | int] = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        data = await self._request("GET", "/v1/logs", params=params)
        if data is None:
            return None
        return LogsPage.from_dict(data)

    async def stats(self) -> list[StatsPoint] | None:
        """Retrieve time-series analytics for the last 30 days.

        Returns:
            A list of :class:`~syvel.models.StatsPoint` objects, or ``None``
            if ``silent=True`` and an error occurred.
        """
        data = await self._request("GET", "/v1/stats")
        if data is None:
            return None
        chart = cast(list[Any], data.get("chart") or [])
        return [StatsPoint.from_dict(point) for point in chart]

    async def list_keys(self) -> list[ApiKey] | None:
        """List all API keys for the authenticated project.

        Returns:
            A list of :class:`~syvel.models.ApiKey` objects, or ``None``
            if ``silent=True`` and an error occurred.
        """
        data = await self._request("GET", "/v1/keys")
        if data is None:
            return None
        items = cast(list[Any], data if isinstance(data, list) else data.get("items") or [])
        return [ApiKey.from_dict(item) for item in items]

    async def create_key(self, name: str) -> ApiKey | None:
        """Create a new API key for the authenticated project.

        Args:
            name: Human-readable label for the new key.

        Returns:
            The created :class:`~syvel.models.ApiKey`, or ``None`` if ``silent=True``
            and an error occurred.
        """
        data = await self._request("POST", "/v1/keys", json={"label": name})
        if data is None:
            return None
        return ApiKey.from_dict(data)

    async def revoke_key(self, key_id: str) -> None:
        """Revoke an API key by its identifier.

        Args:
            key_id: The unique identifier of the key to revoke.
        """
        await self._request("DELETE", f"/v1/keys/{key_id}")

    # -------------------------------------------------------------------------
    # Context manager
    # -------------------------------------------------------------------------

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncSyvel:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, Any] | None:
        try:
            response = await self._http.request(method, path, json=json, params=params)
            return _parse_response(response)
        except SyvelError:
            if self._silent:
                return None
            raise
        except httpx.TimeoutException:
            if self._silent:
                return None
            raise SyvelTimeoutError(self._timeout)
        except Exception:
            if self._silent:
                return None
            raise
