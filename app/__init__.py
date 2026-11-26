"""Flask application factory, security headers, CSRF setup, and error handling."""

from __future__ import annotations

from typing import Any

from flask import Flask, Response, render_template
from flask_wtf.csrf import CSRFError, CSRFProtect

from app.config import Config
from app.db import close_db, init_db_and_seed, reset_and_seed_db
from app.security import hash_password, load_current_user

csrf = CSRFProtect()


def create_app(test_config: dict[str, Any] | type[Config] | None = None) -> Flask:
    """Create and configure the Class Rep Feedback Portal Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config is not None:
        if isinstance(test_config, dict):
            app.config.from_mapping(test_config)
        else:
            app.config.from_object(test_config)

    csrf.init_app(app)
    app.before_request(load_current_user)
    app.teardown_appcontext(close_db)

    from app.routes import register_blueprints

    register_blueprints(app)

    @app.after_request
    def apply_security_headers(response: Response) -> Response:
        """Attach defense-in-depth HTTP security headers to every response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self'; "
            "script-src 'self'; "
            "img-src 'self' data:; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(_error: CSRFError) -> tuple[str, int]:
        return (
            render_template(
                "error.html",
                status_code=400,
                title="Invalid or Expired Security Token",
                message="Your form session expired or failed CSRF verification. Please refresh the page and try again.",
            ),
            400,
        )

    @app.errorhandler(400)
    def handle_bad_request(_error: Exception) -> tuple[str, int]:
        return (
            render_template(
                "error.html",
                status_code=400,
                title="Bad Request",
                message="The submitted request could not be processed.",
            ),
            400,
        )

    @app.errorhandler(403)
    def handle_forbidden(_error: Exception) -> tuple[str, int]:
        return (
            render_template(
                "error.html",
                status_code=403,
                title="Access Denied",
                message="You do not have permission to view or modify this resource.",
            ),
            403,
        )

    @app.errorhandler(404)
    def handle_not_found(_error: Exception) -> tuple[str, int]:
        return (
            render_template(
                "error.html",
                status_code=404,
                title="Page Not Found",
                message="The requested page or feedback item does not exist.",
            ),
            404,
        )

    @app.errorhandler(500)
    def handle_server_error(_error: Exception) -> tuple[str, int]:
        return (
            render_template(
                "error.html",
                status_code=500,
                title="Unexpected Server Error",
                message="An unexpected error occurred. Please try again later.",
            ),
            500,
        )

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Apply SQL migrations and seed fictional demo accounts."""
        init_db_and_seed(app, hash_password)
        print("Database migrated and fictional demo data initialized.")

    @app.cli.command("reset-demo-db")
    def reset_demo_db_command() -> None:
        """Rebuild a fresh local database and reseed fictional demo data (non-production only)."""
        import os

        if os.environ.get("FLASK_ENV", "development").lower() == "production":
            raise RuntimeError("reset-demo-db is disabled when FLASK_ENV=production.")
        applied = reset_and_seed_db(app.config["DATABASE_PATH"], hash_password)
        print(f"Fresh database created (migrations: {', '.join(applied)}) with fictional demo data.")

    if not app.config.get("TESTING", False):
        init_db_and_seed(app, hash_password)

    return app
