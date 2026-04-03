"""Syvel response models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


def _parse_dt(value: str) -> datetime:
    """Parse an ISO 8601 datetime string, handling both 'Z' and '+00:00' suffixes."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of an email or domain risk check.

    All fields are populated for every successful response. The ``email`` field
    contains a masked version of the address (local part partially redacted).

    Attributes:
        email: Masked email address (e.g. ``"a9****e5@yopmail.com"``).
        is_risky: ``True`` when the risk score is ≥ 65. Use this as your primary
            signal to decide whether to accept or reject an address.
        risk_score: Risk score from 0 (safe) to 100 (confirmed disposable).
        reason: Human-readable risk classification:
            ``"safe"`` | ``"disposable"`` | ``"undeliverable"`` | ``"role_account"``.
        deliverability_score: Likelihood (0–100) that mail sent to this address
            will be delivered.
        did_you_mean: A suggested correction when a common typo is detected
            (e.g. ``"hotmail.com"`` for ``"hotmial.com"``), or ``None``.
        is_free_provider: ``True`` for consumer webmail services (Gmail, Yahoo, etc.).
        is_corporate_email: ``True`` when the domain belongs to a business.
        is_alias_email: ``True`` for privacy-relay services (SimpleLogin, AnonAddy, etc.).
        mx_provider_label: Human-readable name of the mail provider, or ``None``.
    """

    email: str
    is_risky: bool
    risk_score: int
    reason: Literal["safe", "disposable", "undeliverable", "role_account"]
    deliverability_score: int
    did_you_mean: str | None
    is_free_provider: bool
    is_corporate_email: bool
    is_alias_email: bool
    mx_provider_label: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckResult:
        return cls(
            email=str(data["email"]),
            is_risky=bool(data["is_risky"]),
            risk_score=int(data["risk_score"]),
            reason=data["reason"],
            deliverability_score=int(data["deliverability_score"]),
            did_you_mean=data.get("did_you_mean") or None,
            is_free_provider=bool(data.get("is_free_provider", False)),
            is_corporate_email=bool(data.get("is_corporate_email", False)),
            is_alias_email=bool(data.get("is_alias_email", False)),
            mx_provider_label=data.get("mx_provider_label") or None,
        )


@dataclass(frozen=True, slots=True)
class UsageResult:
    """Current quota usage for the authenticated project.

    Attributes:
        used: Number of checks performed this month.
        limit: Maximum checks allowed per month on the current plan.
        reset_at: UTC datetime when the monthly quota resets.
        plan: Current plan name (e.g. ``"free"``, ``"starter"``, ``"pro"``).
    """

    used: int
    limit: int
    reset_at: datetime
    plan: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageResult:
        return cls(
            used=int(data["month_count"]),
            limit=int(data["monthly_limit"]),
            reset_at=_parse_dt(str(data["reset_at"])) if data.get("reset_at") else datetime.min,
            plan=str(data.get("plan", "")),
        )


@dataclass(frozen=True, slots=True)
class LogEntry:
    """A single entry from the request log.

    Attributes:
        id: Unique log entry identifier.
        target: The checked email or domain (may be masked).
        is_risky: Whether the check returned a risky result.
        risk_score: Risk score at the time of the check.
        reason: Risk classification at the time of the check.
        created_at: UTC datetime when the check was performed.
    """

    id: str
    target: str
    is_risky: bool
    risk_score: int
    reason: str
    created_at: datetime

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogEntry:
        score = int(data.get("risk_score", 0))
        return cls(
            id=str(data["id"]),
            target=str(data.get("email_domain") or data.get("domain_hash") or ""),
            is_risky=score >= 65,
            risk_score=score,
            reason=str(data.get("reason", "")),
            created_at=_parse_dt(str(data["created_at"])),
        )


@dataclass(frozen=True, slots=True)
class LogsPage:
    """A paginated page of log entries.

    Attributes:
        items: Log entries for this page.
        next_cursor: Cursor value to fetch the next page, or ``None`` if this is
            the last page.
    """

    items: tuple[LogEntry, ...]
    next_cursor: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogsPage:
        raw_items: list[Any] = data.get("items") or []
        return cls(
            items=tuple(LogEntry.from_dict(item) for item in raw_items),
            next_cursor=data.get("next_cursor") or None,
        )


@dataclass(frozen=True, slots=True)
class StatsPoint:
    """A single data point from the time-series analytics.

    Attributes:
        date: Date string in ``YYYY-MM-DD`` format.
        total: Total number of checks on this date.
        risky: Number of risky checks on this date.
    """

    date: str
    total: int
    risky: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StatsPoint:
        return cls(
            date=str(data.get("date", "")),
            total=int(data.get("total_requests", 0)),
            risky=int(data.get("blocked_count", 0)),
        )


@dataclass(frozen=True, slots=True)
class ApiKey:
    """An API key associated with a project.

    Attributes:
        id: Unique key identifier.
        name: Human-readable label for the key.
        prefix: Key prefix shown in the dashboard (e.g. ``"sv_"``).
        created_at: UTC datetime when the key was created.
        last_used_at: UTC datetime of the most recent use, or ``None`` if never used.
    """

    id: str
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiKey:
        last_used = data.get("last_used_at")
        return cls(
            id=str(data["id"]),
            name=str(data.get("label") or ""),
            prefix=str(data.get("key_prefix") or "sv_"),
            created_at=_parse_dt(str(data["created_at"])),
            last_used_at=_parse_dt(str(last_used)) if last_used else None,
        )
