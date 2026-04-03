"""
Django form field validator using Syvel.

This example shows two integration patterns:

1. A standalone validator function that can be attached to any form field.
2. A custom form field subclass with built-in validation.

Setup
-----
Add your API key to settings.py (or load it from an environment variable)::

    # settings.py
    SYVEL_API_KEY = os.environ["SYVEL_API_KEY"]

Install the SDK::

    pip install syvel

Usage
-----
Attach the validator to any EmailField::

    from django import forms
    from myapp.validators import validate_not_disposable

    class SignupForm(forms.Form):
        email = forms.EmailField(validators=[validate_not_disposable])

Or use the custom field directly::

    from myapp.validators import SafeEmailField

    class SignupForm(forms.Form):
        email = SafeEmailField()
"""

from __future__ import annotations

import os

from django.conf import settings  # type: ignore[import-untyped]
from django.core.exceptions import ValidationError  # type: ignore[import-untyped]
from django.forms import EmailField  # type: ignore[import-untyped]

from syvel import Syvel

# Reuse a single client instance across all requests for connection pooling.
_client = Syvel(
    api_key=getattr(settings, "SYVEL_API_KEY", os.environ.get("SYVEL_API_KEY", "")),
    silent=True,  # Fail open: never block a user because of a third-party failure.
)


def validate_not_disposable(value: str) -> None:
    """Django validator that rejects disposable email addresses.

    Silently passes when Syvel is unavailable (fail-open by design).

    Args:
        value: The email address to validate.

    Raises:
        ValidationError: When the email is identified as risky.
    """
    result = _client.check_email(value)
    if result is not None and result.is_risky:
        raise ValidationError(
            "Please use a permanent email address. Disposable addresses are not allowed.",
            code="disposable_email",
        )


class SafeEmailField(EmailField):
    """An EmailField that automatically rejects disposable addresses."""

    def validate(self, value: str) -> None:
        super().validate(value)
        validate_not_disposable(value)
