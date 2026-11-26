"""Blueprint registration for auth, student, and class rep routes."""

from __future__ import annotations

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all route blueprints on the Flask application."""
    from app.routes.auth import auth_bp
    from app.routes.rep import rep_bp
    from app.routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(rep_bp)
