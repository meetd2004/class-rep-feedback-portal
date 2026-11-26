"""Blueprint registration and shared detail rendering helper."""

from __future__ import annotations

from flask import Flask, current_app, g, render_template

from app.db import get_db
from app.security import get_authorized_feedback


def render_feedback_detail(feedback_id: int, *, require_rep_cohort: bool = False) -> str:
    """Authorize and render the feedback detail view in the active role interface."""
    feedback = get_authorized_feedback(
        feedback_id, g.user, require_rep_cohort=require_rep_cohort
    )
    db = get_db()
    responses = db.execute(
        """
        SELECT
            r.id,
            r.message,
            r.created_at,
            u.full_name AS rep_name
        FROM responses AS r
        JOIN users AS u ON u.id = r.rep_id
        WHERE r.feedback_id = ?
        ORDER BY r.created_at ASC, r.id ASC;
        """,
        (feedback_id,),
    ).fetchall()

    allowed_next_statuses = current_app.config["ALLOWED_STATUS_TRANSITIONS"].get(
        feedback["status"], ()
    )

    return render_template(
        "feedback_detail.html",
        feedback=feedback,
        responses=responses,
        allowed_next_statuses=allowed_next_statuses,
    )


def register_blueprints(app: Flask) -> None:
    """Register all route blueprints on the Flask application."""
    from app.routes.auth import auth_bp
    from app.routes.rep import rep_bp
    from app.routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(rep_bp)
