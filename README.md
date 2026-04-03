# syvel

[![PyPI version](https://img.shields.io/pypi/v/syvel?color=blue)](https://pypi.org/project/syvel/)
[![Python versions](https://img.shields.io/pypi/pyversions/syvel)](https://pypi.org/project/syvel/)
[![License](https://img.shields.io/pypi/l/syvel)](LICENSE)
[![CI](https://github.com/syvel-io/syvel-python/actions/workflows/ci.yml/badge.svg)](https://github.com/syvel-io/syvel-python/actions/workflows/ci.yml)

Official Python SDK for [Syvel](https://www.syvel.io) — disposable email detection API.

Detect throwaway addresses, role accounts, and undeliverable domains before they pollute your database. Works with **Python 3.10+**, supports both **sync and async**, and has **zero runtime dependencies** beyond [httpx](https://www.python-httpx.org/).

---

## Install

```bash
pip install syvel
```

---

## Quick start

### Synchronous

```python
import os
from syvel import Syvel, SyvelError, SyvelTimeoutError

client = Syvel(api_key=os.environ["SYVEL_API_KEY"])

try:
    result = client.check_email("user@example.com")
    if result and result.is_risky:
        print(f"Blocked: {result.reason} (score {result.risk_score})")
    else:
        print("Email looks good")
except SyvelTimeoutError:
    pass  # Always fail open on timeouts
except SyvelError as e:
    print(f"API error {e.status_code}: {e}")
```

### Asynchronous

```python
import os
from syvel import AsyncSyvel

async def validate(email: str) -> bool:
    async with AsyncSyvel(api_key=os.environ["SYVEL_API_KEY"]) as client:
        result = await client.check_email(email)
        return result is None or not result.is_risky
```

### Fail-open (silent) mode

When you'd rather accept every user than block one legitimate signup, use `silent=True`. All errors are suppressed and methods return `None`:

```python
client = Syvel(api_key=os.environ["SYVEL_API_KEY"], silent=True)

result = client.check_email("user@example.com")
# Returns None on any error — never blocks your signup flow
if result and result.is_risky:
    print("Risky email detected")
```

---

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | — | **Required.** Your Syvel API key (`sv_...`). Get one at [syvel.io/dashboard](https://www.syvel.io/dashboard). |
| `base_url` | `str` | `https://api.syvel.io` | Override the API base URL (useful for testing). |
| `timeout` | `float` | `3.0` | Request timeout in seconds. |
| `silent` | `bool` | `False` | When `True`, all errors return `None` instead of raising. |

---

## API reference

### `check(domain)`

Check a bare domain for disposable-email risk.

```python
result = client.check("yopmail.com")
```

### `check_email(email)`

Check a full email address. Passes the complete address to the API to enable local-part analysis (role account detection, random pattern scoring).

```python
result = client.check_email("admin@example.com")
```

### `usage()`

Get the current monthly quota and usage for your project.

```python
usage = client.usage()
print(f"{usage.used}/{usage.limit} checks used this month")
```

### `logs(cursor=None, limit=None)`

Retrieve a paginated page of recent request logs.

```python
page = client.logs(limit=50)
for entry in page.items:
    print(entry.target, entry.risk_score)

# Fetch next page
if page.next_cursor:
    next_page = client.logs(cursor=page.next_cursor, limit=50)
```

### `stats()`

Retrieve time-series analytics for the last 30 days.

```python
points = client.stats()
for point in points:
    print(f"{point.date}: {point.total} checks, {point.risky} risky")
```

### `list_keys()` / `create_key(name)` / `revoke_key(key_id)`

Manage API keys for your project.

```python
keys = client.list_keys()

new_key = client.create_key("Staging")
print(new_key.id)

client.revoke_key(new_key.id)
```

All methods are available on `AsyncSyvel` as coroutines — prefix them with `await`.

---

## Response fields

| Field | Type | Description |
|-------|------|-------------|
| `email` | `str` | Masked email address (`"a9****e5@yopmail.com"`). |
| `is_risky` | `bool` | `True` when `risk_score ≥ 65`. Use as your primary signal. |
| `risk_score` | `int` | 0 (safe) → 100 (confirmed disposable). |
| `reason` | `str` | `"safe"` \| `"disposable"` \| `"undeliverable"` \| `"role_account"` |
| `deliverability_score` | `int` | Likelihood (0–100) that mail will be delivered. |
| `did_you_mean` | `str \| None` | Typo correction suggestion (e.g. `"hotmail.com"` for `"hotmial.com"`). |
| `is_free_provider` | `bool` | `True` for Gmail, Yahoo, etc. |
| `is_corporate_email` | `bool` | `True` for business domains. |
| `is_alias_email` | `bool` | `True` for privacy-relay services (SimpleLogin, AnonAddy, etc.). |
| `mx_provider_label` | `str \| None` | Human-readable name of the mail provider. |

---

## Error handling

All errors inherit from `SyvelError`. Catch specific subclasses for fine-grained handling:

```python
from syvel import (
    SyvelError,
    SyvelAuthError,
    SyvelForbiddenError,
    SyvelValidationError,
    SyvelRateLimitError,
    SyvelTimeoutError,
)

try:
    result = client.check_email("user@example.com")
except SyvelAuthError:
    # Invalid or missing API key
    print("Check your SYVEL_API_KEY")
except SyvelRateLimitError as e:
    # Monthly quota exceeded
    print(f"Quota resets at {e.reset_at}")
except SyvelTimeoutError:
    # Request took longer than `timeout` seconds
    pass  # Always fail open
except SyvelValidationError:
    # Invalid email or domain format
    pass
except SyvelForbiddenError:
    # Origin not whitelisted for this API key
    pass
except SyvelError as e:
    # Catch-all for unexpected API errors
    print(f"Syvel error {e.status_code}: {e}")
```

| Exception | HTTP | Cause |
|-----------|------|-------|
| `SyvelAuthError` | 401 | Invalid or missing API key |
| `SyvelForbiddenError` | 403 | Origin not authorised for this key |
| `SyvelValidationError` | 422 | Invalid email or domain format |
| `SyvelRateLimitError` | 429 | Monthly quota exceeded |
| `SyvelTimeoutError` | — | Request exceeded the configured timeout |
| `SyvelError` | any | Unexpected API error |

---

## Framework examples

### Django

```python
# validators.py
import os
from django.core.exceptions import ValidationError
from syvel import Syvel

_client = Syvel(api_key=os.environ["SYVEL_API_KEY"], silent=True)

def validate_not_disposable(value: str) -> None:
    result = _client.check_email(value)
    if result and result.is_risky:
        raise ValidationError(
            "Please use a permanent email address.",
            code="disposable_email",
        )

# forms.py
from django import forms
from .validators import validate_not_disposable

class SignupForm(forms.Form):
    email = forms.EmailField(validators=[validate_not_disposable])
```

### FastAPI

```python
import os
from functools import lru_cache
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException
from syvel import AsyncSyvel, CheckResult

app = FastAPI()

@lru_cache(maxsize=1)
def get_client() -> AsyncSyvel:
    return AsyncSyvel(api_key=os.environ["SYVEL_API_KEY"], silent=True)

async def email_risk(
    email: str,
    client: AsyncSyvel = Depends(get_client),
) -> CheckResult | None:
    return await client.check_email(email)

EmailRisk = Annotated[CheckResult | None, Depends(email_risk)]

@app.post("/signup")
async def signup(email: str, risk: EmailRisk):
    if risk and risk.is_risky:
        raise HTTPException(422, f"Disposable email not allowed ({risk.reason})")
    return {"status": "ok"}
```

### Flask

```python
import os
from flask import Flask, abort, request
from syvel import Syvel

app = Flask(__name__)
_client = Syvel(api_key=os.environ["SYVEL_API_KEY"], silent=True)

@app.before_request
def check_email():
    if request.endpoint == "register" and request.method == "POST":
        email = request.form.get("email", "")
        result = _client.check_email(email)
        if result and result.is_risky:
            abort(422, "Disposable email addresses are not allowed.")
```

---

## Context manager

Use `Syvel` or `AsyncSyvel` as a context manager to ensure connections are released when you're done:

```python
# Sync
with Syvel(api_key="sv_...") as client:
    result = client.check("yopmail.com")

# Async
async with AsyncSyvel(api_key="sv_...") as client:
    result = await client.check("yopmail.com")
```

For long-lived processes (web servers), create the client once at startup and call `client.close()` / `await client.aclose()` on shutdown instead.

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

```bash
git clone https://github.com/syvel-io/syvel-python.git
cd syvel-python
pip install -e ".[dev]"

# Run tests
pytest

# Lint + type-check
ruff check src tests
mypy src
```

---

## License

[MIT](LICENSE)
