"""
FastAPI async dependency for email risk checking.

This example shows how to integrate Syvel into a FastAPI application using
dependency injection. The client is shared across all requests via
``@lru_cache``, ensuring a single ``AsyncClient`` instance and connection pool.

Setup
-----
::

    pip install syvel fastapi

Usage
-----
::

    from fastapi import FastAPI, HTTPException, Depends
    from pydantic import BaseModel
    from examples.fastapi_dependency import EmailRisk, check_email_risk

    app = FastAPI()

    class SignupRequest(BaseModel):
        email: str
        password: str

    @app.post("/signup")
    async def signup(
        body: SignupRequest,
        risk: EmailRisk = Depends(check_email_risk),
    ):
        if risk is not None and risk.is_risky:
            raise HTTPException(
                status_code=422,
                detail={
                    "field": "email",
                    "message": "Disposable email addresses are not allowed.",
                    "reason": risk.reason,
                },
            )
        # ... create user
        return {"status": "ok"}

Shutdown
--------
Close the client when the app shuts down::

    @app.on_event("shutdown")
    async def shutdown():
        client = get_syvel_client()
        await client.aclose()
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Query  # type: ignore[import-untyped]

from syvel import AsyncSyvel, CheckResult


@lru_cache(maxsize=1)
def get_syvel_client() -> AsyncSyvel:
    """Return a shared ``AsyncSyvel`` client (created once per process)."""
    return AsyncSyvel(
        api_key=os.environ["SYVEL_API_KEY"],
        silent=True,  # Fail open: never block a user because of a third-party failure.
    )


async def check_email_risk(
    email: str = Query(..., description="Email address to check"),
    client: AsyncSyvel = Depends(get_syvel_client),
) -> CheckResult | None:
    """FastAPI dependency that returns the Syvel risk result for *email*.

    Returns ``None`` when Syvel is unavailable (fail-open).
    """
    return await client.check_email(email)


# Type alias for use in route signatures.
EmailRisk = Annotated[CheckResult | None, Depends(check_email_risk)]
