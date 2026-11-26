"""Student workflow routes: dashboard, feedback CRUD, and shared detail view."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from app.db import get_db, utc_now_iso
from app.security import (
    get_authorized_feedback,
    login_required,
    role_required,
    validate_feedback_input,
)

student_bp = Blueprint("student", __name__)


@student_bp.route("/student/dashboard")
@role_required("student")
def dashboard() -> str:
    """Display only the signed-in student's own feedback submissions."""
    db = get_db()
    submissions = db.execute(
        """
        SELECT
            f.id,
            f.title,
            f.category,
            f.status,
            f.created_at,
            f.updated_at,
            (SELECT COUNT(*) FROM responses AS r WHERE r.feedback_id = f.id) AS response_count
        FROM feedback AS f
        WHERE f.author_id = ? AND f.cohort = ?
        ORDER BY f.updated_at DESC, f.id DESC;
        """,
        (g.user["id"], g.user["cohort"]),
    ).fetchall()

    counts = {
        "total": len(submissions),
        "New": sum(1 for row in submissions if row["status"] == "New"),
        "In Review": sum(1 for row in submissions if row["status"] == "In Review"),
        "Resolved": sum(1 for row in submissions if row["status"] == "Resolved"),
    }

    return render_template(
        "student_dashboard.html",
        submissions=submissions,
        counts=counts,
    )


@student_bp.route("/feedback/new", methods=["GET", "POST"])
@role_required("student")
def create_feedback() -> object:
    """Create a new feedback submission always initialized to status 'New'."""
    categories = current_app.config["ALLOWED_CATEGORIES"]
    form_data = {"title": "", "category": "", "description": ""}
    errors: dict[str, str] = {}

    if request.method == "POST":
        form_data, errors = validate_feedback_input(
            request.form.get("title", ""),
            request.form.get("category", ""),
            request.form.get("description", ""),
            categories,
        )
        if not errors:
            now = utc_now_iso()
            db = get_db()
            cursor = db.execute(
                """
                INSERT INTO feedback (
                    author_id, cohort, title, category, description, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'New', ?, ?);
                """,
                (
                    g.user["id"],
                    g.user["cohort"],
                    form_data["title"],
                    form_data["category"],
                    form_data["description"],
                    now,
                    now,
                ),
            )
            db.commit()
            flash("Your feedback has been submitted with status New.", "success")
            return redirect(url_for("student.view_feedback", feedback_id=cursor.lastrowid))

    return render_template(
        "feedback_form.html",
        mode="create",
        categories=categories,
        form_data=form_data,
        errors=errors,
        feedback=None,
    )


@student_bp.route("/feedback/<int:feedback_id>")
@login_required
def view_feedback(feedback_id: int) -> str:
    """View a feedback item and its rep responses (author student or assigned rep only)."""
    feedback = get_authorized_feedback(feedback_id, g.user)
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


@student_bp.route("/feedback/<int:feedback_id>/edit", methods=["GET", "POST"])
@role_required("student")
def edit_feedback(feedback_id: int) -> object:
    """Allow a student to edit their own feedback only while its status is 'New'."""
    feedback = get_authorized_feedback(feedback_id, g.user, require_owner_new=True)
    categories = current_app.config["ALLOWED_CATEGORIES"]
    form_data = {
        "title": feedback["title"],
        "category": feedback["category"],
        "description": feedback["description"],
    }
    errors: dict[str, str] = {}

    if request.method == "POST":
        form_data, errors = validate_feedback_input(
            request.form.get("title", ""),
            request.form.get("category", ""),
            request.form.get("description", ""),
            categories,
        )
        if not errors:
            db = get_db()
            db.execute(
                """
                UPDATE feedback
                SET title = ?, category = ?, description = ?, updated_at = ?
                WHERE id = ? AND author_id = ? AND status = 'New';
                """,
                (
                    form_data["title"],
                    form_data["category"],
                    form_data["description"],
                    utc_now_iso(),
                    feedback_id,
                    g.user["id"],
                ),
            )
            db.commit()
            flash("Feedback updated successfully.", "success")
            return redirect(url_for("student.view_feedback", feedback_id=feedback_id))

    return render_template(
        "feedback_form.html",
        mode="edit",
        categories=categories,
        form_data=form_data,
        errors=errors,
        feedback=feedback,
    )


@student_bp.route("/feedback/<int:feedback_id>/delete", methods=["POST"])
@role_required("student")
def delete_feedback(feedback_id: int) -> object:
    """Allow a student to delete their own feedback only while its status is 'New'."""
    get_authorized_feedback(feedback_id, g.user, require_owner_new=True)
    db = get_db()
    db.execute(
        "DELETE FROM feedback WHERE id = ? AND author_id = ? AND status = 'New';",
        (feedback_id, g.user["id"]),
    )
    db.commit()
    flash("Feedback submission deleted.", "info")
    return redirect(url_for("student.dashboard"))
