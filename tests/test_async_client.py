"""Unit tests for the asynchronous AsyncSyvel client."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from syvel import AsyncSyvel
from syvel.exceptions import (
    SyvelAuthError,
    SyvelError,
    SyvelForbiddenError,
    SyvelRateLimitError,
    SyvelTimeoutError,
    SyvelValidationError,
)
from syvel.models import ApiKey, CheckResult, LogsPage, StatsPoint, UsageResult
from tests.conftest import SAFE_RESULT, SAMPLE_RESULT

# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    async def test_raises_when_api_key_is_empty(self) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            AsyncSyvel(api_key="")

    async def test_strips_trailing_slash_from_base_url(self) -> None:
        client = AsyncSyvel(api_key="sv_test", base_url="https://api.syvel.io/")
        assert client._base_url == "https://api.syvel.io"
        await client.aclose()

    async def test_defaults(self) -> None:
        client = AsyncSyvel(api_key="sv_test")
        assert client._timeout == 3.0
        assert client._silent is False
        await client.aclose()


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


class TestCheck:
    async def test_returns_check_result(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(200, json=SAMPLE_RESULT)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                result = await client.check("yopmail.com")

        assert isinstance(result, CheckResult)
        assert result.is_risky is True
        assert result.risk_score == 100
        assert result.reason == "disposable"

    async def test_sends_authorization_header(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            route = respx.get(f"{base_url}/v1/check/gmail.com").mock(
                return_value=httpx.Response(200, json=SAFE_RESULT)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                await client.check("gmail.com")

        assert route.called
        request = route.calls[0].request
        assert request.headers["authorization"] == f"Bearer {api_key}"

    async def test_sends_user_agent_header(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            route = respx.get(f"{base_url}/v1/check/gmail.com").mock(
                return_value=httpx.Response(200, json=SAFE_RESULT)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                await client.check("gmail.com")

        request = route.calls[0].request
        assert request.headers["user-agent"].startswith("syvel-python/")

    async def test_custom_base_url(self) -> None:
        with respx.mock:
            respx.get("https://custom.example.com/v1/check/yopmail.com").mock(
                return_value=httpx.Response(200, json=SAMPLE_RESULT)
            )
            async with AsyncSyvel(
                api_key="sv_test", base_url="https://custom.example.com"
            ) as client:
                result = await client.check("yopmail.com")

        assert result is not None
        assert result.is_risky is True

    async def test_url_encodes_special_characters(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            route = respx.get(f"{base_url}/v1/check/test%2Bdomain.com").mock(
                return_value=httpx.Response(200, json=SAFE_RESULT)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                await client.check("test+domain.com")

        assert route.called


# ---------------------------------------------------------------------------
# check_email()
# ---------------------------------------------------------------------------


class TestCheckEmail:
    async def test_url_encodes_at_symbol(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            route = respx.get(f"{base_url}/v1/check/user%40yopmail.com").mock(
                return_value=httpx.Response(200, json=SAMPLE_RESULT)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                await client.check_email("user@yopmail.com")

        assert route.called

    async def test_raises_on_missing_at_symbol(self, api_key: str) -> None:
        async with AsyncSyvel(api_key=api_key) as client:
            with pytest.raises(SyvelError, match="@"):
                await client.check_email("notanemail")

    async def test_silent_mode_returns_none_on_invalid_email(
        self, api_key: str
    ) -> None:
        async with AsyncSyvel(api_key=api_key, silent=True) as client:
            result = await client.check_email("notanemail")
        assert result is None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    async def test_401_raises_auth_error(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(401, json={"message": "Unauthorized"})
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(SyvelAuthError) as exc_info:
                    await client.check("yopmail.com")

        assert exc_info.value.status_code == 401
        assert exc_info.value.code == "UNAUTHORIZED"

    async def test_403_raises_forbidden_error(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(403, json={"message": "Forbidden"})
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(SyvelForbiddenError) as exc_info:
                    await client.check("yopmail.com")

        assert exc_info.value.status_code == 403

    async def test_422_raises_validation_error(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/bad").mock(
                return_value=httpx.Response(422, json={"detail": "Invalid domain format"})
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(SyvelValidationError) as exc_info:
                    await client.check("bad")

        assert exc_info.value.status_code == 422
        assert "Invalid domain format" in str(exc_info.value)

    async def test_429_raises_rate_limit_error_with_reset_at(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(
                    429, json={"reset_at": "2026-05-01T00:00:00Z"}
                )
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(SyvelRateLimitError) as exc_info:
                    await client.check("yopmail.com")

        assert exc_info.value.reset_at == datetime(2026, 5, 1, tzinfo=timezone.utc)

    async def test_429_raises_rate_limit_error_without_reset_at(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(429, json={})
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(SyvelRateLimitError) as exc_info:
                    await client.check("yopmail.com")

        assert exc_info.value.reset_at is None

    async def test_500_raises_syvel_error_with_message(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(500, json={"message": "Internal server error"})
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(SyvelError) as exc_info:
                    await client.check("yopmail.com")

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value)

    async def test_500_with_invalid_json_raises_syvel_error(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(500, content=b"not json")
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(SyvelError) as exc_info:
                    await client.check("yopmail.com")

        assert "HTTP 500" in str(exc_info.value)

    async def test_timeout_raises_timeout_error(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                side_effect=httpx.TimeoutException("timed out")
            )
            async with AsyncSyvel(api_key=api_key, timeout=1.0) as client:
                with pytest.raises(SyvelTimeoutError) as exc_info:
                    await client.check("yopmail.com")

        assert exc_info.value.timeout_s == 1.0

    async def test_network_error_raises_in_non_silent_mode(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                side_effect=httpx.NetworkError("connection refused")
            )
            async with AsyncSyvel(api_key=api_key) as client:
                with pytest.raises(httpx.NetworkError):
                    await client.check("yopmail.com")


# ---------------------------------------------------------------------------
# Silent mode
# ---------------------------------------------------------------------------


class TestSilentMode:
    async def test_network_error_returns_none(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                side_effect=httpx.NetworkError("connection refused")
            )
            async with AsyncSyvel(api_key=api_key, silent=True) as client:
                result = await client.check("yopmail.com")

        assert result is None

    async def test_401_returns_none(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(401, json={})
            )
            async with AsyncSyvel(api_key=api_key, silent=True) as client:
                result = await client.check("yopmail.com")

        assert result is None

    async def test_429_returns_none(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                return_value=httpx.Response(429, json={})
            )
            async with AsyncSyvel(api_key=api_key, silent=True) as client:
                result = await client.check("yopmail.com")

        assert result is None

    async def test_timeout_returns_none(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/yopmail.com").mock(
                side_effect=httpx.TimeoutException("timed out")
            )
            async with AsyncSyvel(api_key=api_key, silent=True) as client:
                result = await client.check("yopmail.com")

        assert result is None


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    async def test_async_context_manager_closes_client(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/check/gmail.com").mock(
                return_value=httpx.Response(200, json=SAFE_RESULT)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                result = await client.check("gmail.com")

        assert result is not None
        assert result.is_risky is False


# ---------------------------------------------------------------------------
# P1 methods
# ---------------------------------------------------------------------------


class TestP1Methods:
    async def test_usage_returns_usage_result(self, api_key: str, base_url: str) -> None:
        payload = {
            "plan": "pro",
            "monthly_limit": 10000,
            "month_count": 250,
            "remaining_month": 9750,
            "reset_at": "2026-05-01T00:00:00Z",
        }
        with respx.mock:
            respx.get(f"{base_url}/v1/usage").mock(
                return_value=httpx.Response(200, json=payload)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                result = await client.usage()

        assert isinstance(result, UsageResult)
        assert result.used == 250
        assert result.limit == 10000
        assert result.plan == "pro"

    async def test_logs_returns_logs_page(self, api_key: str, base_url: str) -> None:
        payload = {
            "items": [
                {
                    "id": "log_1",
                    "email_domain": "yopmail.com",
                    "risk_score": 100,
                    "reason": "disposable",
                    "created_at": "2026-04-01T10:00:00Z",
                }
            ],
            "next_cursor": None,
        }
        with respx.mock:
            respx.get(f"{base_url}/v1/logs").mock(
                return_value=httpx.Response(200, json=payload)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                result = await client.logs()

        assert isinstance(result, LogsPage)
        assert len(result.items) == 1
        assert result.next_cursor is None

    async def test_logs_passes_cursor_and_limit(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            route = respx.get(f"{base_url}/v1/logs").mock(
                return_value=httpx.Response(200, json={"items": [], "next_cursor": None})
            )
            async with AsyncSyvel(api_key=api_key) as client:
                await client.logs(cursor="abc", limit=10)

        request = route.calls[0].request
        assert "cursor=abc" in str(request.url)
        assert "limit=10" in str(request.url)

    async def test_stats_returns_list_of_stats_points(
        self, api_key: str, base_url: str
    ) -> None:
        payload = {
            "chart": [
                {"date": "2026-04-01", "total_requests": 50, "blocked_count": 8},
            ]
        }
        with respx.mock:
            respx.get(f"{base_url}/v1/stats").mock(
                return_value=httpx.Response(200, json=payload)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                result = await client.stats()

        assert result is not None
        assert isinstance(result[0], StatsPoint)
        assert result[0].total == 50

    async def test_list_keys_returns_api_keys(self, api_key: str, base_url: str) -> None:
        payload = [
            {
                "id": "key_1",
                "label": "Production",
                "key_prefix": "sv_",
                "created_at": "2026-01-01T00:00:00Z",
                "last_used_at": "2026-04-01T00:00:00Z",
            }
        ]
        with respx.mock:
            respx.get(f"{base_url}/v1/keys").mock(
                return_value=httpx.Response(200, json=payload)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                result = await client.list_keys()

        assert result is not None
        assert isinstance(result[0], ApiKey)
        assert result[0].last_used_at is not None

    async def test_create_key_sends_post(self, api_key: str, base_url: str) -> None:
        payload = {
            "id": "key_3",
            "label": "CI",
            "key_prefix": "sv_",
            "created_at": "2026-04-01T00:00:00Z",
            "last_used_at": None,
        }
        with respx.mock:
            route = respx.post(f"{base_url}/v1/keys").mock(
                return_value=httpx.Response(200, json=payload)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                result = await client.create_key("CI")

        assert result is not None
        assert result.name == "CI"
        assert route.called

    async def test_revoke_key_sends_delete(self, api_key: str, base_url: str) -> None:
        with respx.mock:
            route = respx.delete(f"{base_url}/v1/keys/key_1").mock(
                return_value=httpx.Response(204)
            )
            async with AsyncSyvel(api_key=api_key) as client:
                await client.revoke_key("key_1")

        assert route.called

    async def test_p1_methods_return_none_in_silent_mode_on_error(
        self, api_key: str, base_url: str
    ) -> None:
        with respx.mock:
            respx.get(f"{base_url}/v1/usage").mock(return_value=httpx.Response(401, json={}))
            respx.get(f"{base_url}/v1/logs").mock(return_value=httpx.Response(401, json={}))
            respx.get(f"{base_url}/v1/stats").mock(return_value=httpx.Response(401, json={}))
            respx.get(f"{base_url}/v1/keys").mock(return_value=httpx.Response(401, json={}))
            respx.post(f"{base_url}/v1/keys").mock(return_value=httpx.Response(401, json={}))
            async with AsyncSyvel(api_key=api_key, silent=True) as client:
                assert await client.usage() is None
                assert await client.logs() is None
                assert await client.stats() is None
                assert await client.list_keys() is None
                assert await client.create_key("x") is None
