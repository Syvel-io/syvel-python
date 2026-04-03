"""
Flask extension for email risk validation using Syvel.

This example provides a ``SyvelFlask`` extension class and a standalone
``init_syvel`` helper. The client is initialised once at startup and
shared across all requests.

Setup
-----
::

    pip install syvel flask

Usage
-----
Using the extension class::

    from flask import Flask
    from examples.flask_extension import SyvelFlask

    app = Flask(__name__)
    app.config["SYVEL_API_KEY"] = os.environ["SYVEL_API_KEY"]

    syvel_ext = SyvelFlask()
    syvel_ext.init_app(app)

Using the helper function::

    from flask import Flask
    from examples.flask_extension import init_syvel

    app = Flask(__name__)
    init_syvel(app, protected_endpoints={"register", "signup"})

In your view, abort with 422 when the email is risky::

    from flask import request, abort, g

    @app.route("/register", methods=["POST"])
    def register():
        # g.syvel_result is set by the before_request hook
        if g.get("syvel_result") and g.syvel_result.is_risky:
            abort(422, "Disposable email addresses are not allowed.")
        # ... create user
"""

from __future__ import annotations

import os

from flask import Flask, abort, g, request  # type: ignore[import-untyped]

from syvel import Syvel


class SyvelFlask:
    """Flask extension that validates email addresses before protected endpoints.

    Attach to a Flask app via :meth:`init_app` (application factory pattern)
    or pass the app directly to the constructor.
    """

    def __init__(self, app: Flask | None = None) -> None:
        self._client: Syvel | None = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask, *, protected_endpoints: set[str] | None = None) -> None:
        """Initialise the extension with a Flask application.

        Args:
            app: The Flask application instance.
            protected_endpoints: Set of endpoint names (view function names) that
                trigger email validation. When ``None``, defaults to
                ``{"register", "signup"}``.
        """
        api_key = app.config.get("SYVEL_API_KEY") or os.environ.get("SYVEL_API_KEY", "")
        self._client = Syvel(api_key=api_key, silent=True)
        guarded = protected_endpoints or {"register", "signup"}

        @app.before_request
        def _check_email() -> None:
            if request.endpoint not in guarded:
                return
            email = (request.form.get("email") or request.json or {}).get("email", "")  # type: ignore[union-attr]
            if not email:
                return
            assert self._client is not None
            result = self._client.check_email(str(email))
            g.syvel_result = result
            if result is not None and result.is_risky:
                abort(422, "Disposable email addresses are not allowed.")

        @app.teardown_appcontext
        def _close_client(_: BaseException | None) -> None:
            pass  # httpx.Client is reused across requests; close on app shutdown.

        app.extensions["syvel"] = self

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            self._client.close()


def init_syvel(
    app: Flask,
    *,
    protected_endpoints: set[str] | None = None,
) -> SyvelFlask:
    """Convenience helper to attach the Syvel extension to *app*.

    Returns the :class:`SyvelFlask` extension instance.
    """
    ext = SyvelFlask()
    ext.init_app(app, protected_endpoints=protected_endpoints)
    return ext
