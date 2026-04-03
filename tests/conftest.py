"""Shared test fixtures."""

import pytest

SAMPLE_RESULT = {
    "email": "a9****e5@yopmail.com",
    "is_risky": True,
    "risk_score": 100,
    "reason": "disposable",
    "deliverability_score": 0,
    "did_you_mean": None,
    "is_free_provider": False,
    "is_corporate_email": False,
    "is_alias_email": False,
    "mx_provider_label": "Yopmail",
}

SAFE_RESULT = {
    "email": "us****r@gmail.com",
    "is_risky": False,
    "risk_score": 5,
    "reason": "safe",
    "deliverability_score": 95,
    "did_you_mean": None,
    "is_free_provider": True,
    "is_corporate_email": False,
    "is_alias_email": False,
    "mx_provider_label": "Google",
}


@pytest.fixture
def api_key() -> str:
    return "sv_test_key"


@pytest.fixture
def base_url() -> str:
    return "https://api.syvel.io"
