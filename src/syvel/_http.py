"""Internal HTTP utilities shared by the sync and async clients."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from syvel._version import __version__
from syvel.exceptions import (
    SyvelAuthError,
    SyvelError,
    SyvelForbiddenError,
    SyvelRateLimitError,
    SyvelValidationError,
)

DEFAULT_BASE_URL = "https://api.syvel.io"
DEFAULT_TIMEOUT = 3.0


def _make_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": f"syvel-python/{__version__}",
        "Accept": "application/json",
    }


def _encode_target(target: str) -> str:
    """Percent-encode an email or domain for use in a URL path segment.

    Equivalent to JavaScript's ``encodeURIComponent``: encodes every character
    that is not unreserved, including ``@``, ``+``, and ``/``.
    """
    return quote(target, safe="")


def _validate_email(email: str, *, silent: bool) -> bool:
    """Check that *email* contains an ``@`` character.

    Returns ``True`` when the email is valid.
    Raises :class:`~syvel.exceptions.SyvelError` when invalid and ``silent`` is ``False``.
    Returns ``False`` when invalid and ``silent`` is ``True``.
    """
    if "@" not in email:
        if silent:
            return False
        raise SyvelError(
            f"Invalid email address: {email!r}. Expected a string containing '@'.",
            code="INVALID_EMAIL",
        )
    return True


def _try_json(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
        if isinstance(data, list):
            return {"items": data}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    """Map an httpx response to a parsed dict or raise a typed Syvel exception."""
    if response.is_success:
        return _try_json(response)

    status = response.status_code

    if status == 401:
        raise SyvelAuthError()

    if status == 403:
        raise SyvelForbiddenError()

    if status == 422:
        body = _try_json(response)
        detail = body.get("detail")
        raise SyvelValidationError(str(detail) if detail else None)

    if status == 429:
        body = _try_json(response)
        reset_str = body.get("reset_at")
        reset_at = _parse_datetime(str(reset_str)) if reset_str else None
        raise SyvelRateLimitError(reset_at)

    body = _try_json(response)
    message = body.get("message") or body.get("detail") or f"HTTP {status}"
    raise SyvelError(str(message), status_code=status)
