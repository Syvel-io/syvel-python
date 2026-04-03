# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-04-03

### Added

- `Syvel` synchronous client with `check()` and `check_email()` methods.
- `AsyncSyvel` asynchronous client with an identical API (`async`/`await`).
- P1 endpoints on both clients: `usage()`, `logs()`, `stats()`, `list_keys()`,
  `create_key()`, `revoke_key()`.
- Full typed exception hierarchy:
  - `SyvelError` — base class with `status_code` and `code` attributes.
  - `SyvelAuthError` — HTTP 401, invalid or missing API key.
  - `SyvelForbiddenError` — HTTP 403, origin not authorised.
  - `SyvelValidationError` — HTTP 422, invalid email or domain format.
  - `SyvelRateLimitError` — HTTP 429, quota exceeded. Exposes `reset_at: datetime | None`.
  - `SyvelTimeoutError` — request exceeded the configured timeout.
- Silent mode (`silent=True`) for automatic fail-open behaviour.
- Context manager support for both sync (`with`) and async (`async with`) clients.
- Response models as frozen dataclasses: `CheckResult`, `UsageResult`, `LogEntry`,
  `LogsPage`, `StatsPoint`, `ApiKey`.
- `py.typed` marker — PEP 561 compliant for full type-checker support.
- Integration examples for Django, FastAPI, and Flask.
- GitHub Actions CI matrix across Python 3.10–3.13.
- PyPI Trusted Publishing (OIDC) workflow — no stored tokens.

[Unreleased]: https://github.com/syvel-io/syvel-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/syvel-io/syvel-python/releases/tag/v0.1.0
