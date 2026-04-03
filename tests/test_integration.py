"""Real-API integration tests.

These tests make live HTTP requests to api.syvel.io and are skipped automatically
when the ``SYVEL_API_KEY`` environment variable is not set.

Run them with::

    SYVEL_API_KEY=sv_... pytest tests/test_integration.py -v
"""

from __future__ import annotations

import os

import pytest

from syvel import AsyncSyvel, Syvel
from syvel.exceptions import SyvelAuthError, SyvelValidationError

API_KEY = os.environ.get("SYVEL_API_KEY")

pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="SYVEL_API_KEY environment variable is not set",
)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


class TestSyncIntegration:
    def test_check_known_disposable_domain(self) -> None:
        assert API_KEY is not None
        client = Syvel(api_key=API_KEY)
        result = client.check("yopmail.com")
        assert result is not None
        assert result.is_risky is True
        assert result.risk_score == 100
        assert result.reason == "disposable"

    def test_check_safe_domain(self) -> None:
        assert API_KEY is not None
        client = Syvel(api_key=API_KEY)
        result = client.check("gmail.com")
        assert result is not None
        assert result.is_risky is False

    def test_check_result_has_all_fields(self) -> None:
        assert API_KEY is not None
        client = Syvel(api_key=API_KEY)
        result = client.check("yopmail.com")
        assert result is not None
        assert isinstance(result.email, str)
        assert isinstance(result.is_risky, bool)
        assert isinstance(result.risk_score, int)
        assert result.reason in ("safe", "disposable", "undeliverable", "role_account")
        assert isinstance(result.deliverability_score, int)
        assert isinstance(result.is_free_provider, bool)
        assert isinstance(result.is_corporate_email, bool)
        assert isinstance(result.is_alias_email, bool)

    def test_check_email_passes_full_address(self) -> None:
        assert API_KEY is not None
        client = Syvel(api_key=API_KEY)
        result = client.check_email("user@yopmail.com")
        assert result is not None
        assert result.is_risky is True

    def test_invalid_api_key_raises_auth_error(self) -> None:
        client = Syvel(api_key="sv_this_key_is_intentionally_invalid_for_testing")
        with pytest.raises(SyvelAuthError):
            client.check("gmail.com")

    def test_invalid_domain_raises_validation_error(self) -> None:
        assert API_KEY is not None
        client = Syvel(api_key=API_KEY)
        with pytest.raises(SyvelValidationError):
            client.check("not a valid domain !!!")


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


class TestAsyncIntegration:
    async def test_check_known_disposable_domain(self) -> None:
        assert API_KEY is not None
        async with AsyncSyvel(api_key=API_KEY) as client:
            result = await client.check("yopmail.com")
        assert result is not None
        assert result.is_risky is True
        assert result.risk_score == 100

    async def test_check_safe_domain(self) -> None:
        assert API_KEY is not None
        async with AsyncSyvel(api_key=API_KEY) as client:
            result = await client.check("gmail.com")
        assert result is not None
        assert result.is_risky is False

    async def test_check_email_passes_full_address(self) -> None:
        assert API_KEY is not None
        async with AsyncSyvel(api_key=API_KEY) as client:
            result = await client.check_email("user@yopmail.com")
        assert result is not None
        assert result.is_risky is True

    async def test_invalid_api_key_raises_auth_error(self) -> None:
        async with AsyncSyvel(
            api_key="sv_this_key_is_intentionally_invalid_for_testing"
        ) as client:
            with pytest.raises(SyvelAuthError):
                await client.check("gmail.com")
