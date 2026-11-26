"""Class rep workflow routes: filtered cohort queue, responses, and status progression."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for

from app.db import get_db, utc_now_iso
from app.security import (
    get_authorized_feedback,
    role_required,
    validate_response_input,
    validate_status_transition,
)

rep_bp = Blueprint("rep", __name__, url_prefix="/rep")


@rep_bp.route("/dashboard")
@role_required("rep")
def dashboard() -> str:
    """Display all feedback for the rep's assigned cohort with safe category/status filters."""
    categories = current_app.config["ALLOWED_CATEGORIES"]
    statuses = current_app.config["ALLOWED_STATUSES"]

    selected_category = request.args.get("category", "").strip()
    selected_status = request.args.get("status", "").strip()

    if selected_category not in categories:
        selected_category = ""
    if selected_status not in statuses:
        selected_status = ""

    db = get_db()

    # Summary counts across the entire assigned cohort
    summary_rows = db.execute(
        "SELECT status, COUNT(*) AS cnt FROM feedback WHERE cohort = ? GROUP BY status;",
        (g.user["cohort"],),
    ).fetchall()
    counts = {"total": 0, "New": 0, "In Review": 0, "Resolved": 0}
    for row in summary_rows:
        counts[row["status"]] = row["cnt"]
        counts["total"] += row["cnt"]

    submissions = db.execute(
        """
        SELECT
            f.id,
            f.title,
            f.category,
            f.status,
            f.created_at,
            f.updated_at,
            u.full_name AS author_name,
            (SELECT COUNT(*) FROM responses AS r WHERE r.feedback_id = f.id) AS response_count
        FROM feedback AS f
        JOIN users AS u ON u.id = f.author_id
        WHERE f.cohort = ?
          AND (? = '' OR f.category = ?)
          AND (? = '' OR f.status = ?)
        ORDER BY
            CASE f.status
                WHEN 'New' THEN 1
                WHEN 'In Review' THEN 2
                ELSE 3
            END,
            f.updated_at DESC,
            f.id DESC;
        """,
        (
            g.user["cohort"],
            selected_category,
            selected_category,
            selected_status,
            selected_status,
        ),
    ).fetchall()

    return render_template(
        "rep_dashboard.html",
        submissions=submissions,
        categories=categories,
        statuses=statuses,
        selected_category=selected_category,
        selected_status=selected_status,
        counts=counts,
    )


@rep_bp.route("/feedback/<int:feedback_id>/respond", methods=["POST"])
@role_required("rep")
def add_response(feedback_id: int) -> object:
    """Post an official class rep response and advance New items to In Review."""
    feedback = get_authorized_feedback(feedback_id, g.user, require_rep_cohort=True)
    cleaned_message, error = validate_response_input(request.form.get("message", ""))

    if error is not None:
        flash(error, "danger")
        return redirect(url_for("student.view_feedback", feedback_id=feedback_id))

    now = utc_now_iso()
    db = get_db()
    db.execute(
        """
        INSERT INTO responses (feedback_id, rep_id, message, created_at)
        VALUES (?, ?, ?, ?);
        """,
        (feedback_id, g.user["id"], cleaned_message, now),
    )

    # Automatically move 'New' -> 'In Review' once a rep responds so the item is locked from student edits/deletion.
    new_status = "In Review" if feedback["status"] == "New" else feedback["status"]
    db.execute(
        "UPDATE feedback SET status = ?, updated_at = ? WHERE id = ?;",
        (new_status, now, feedback_id),
    )
    db.commit()

    if feedback["status"] == "New":
        flash("Response posted and submission status moved to In Review.", "success")
    else:
        flash("Response posted.", "success")

    return redirect(url_for("student.view_feedback", feedback_id=feedback_id))


@rep_bp.route("/feedback/<int:feedback_id>/status", methods=["POST"])
@role_required("rep")
def update_status(feedback_id: int) -> object:
    """Advance feedback status along the allowed workflow (New -> In Review -> Resolved)."""
    feedback = get_authorized_feedback(feedback_id, g.user, require_rep_cohort=True)
    target_status = request.form.get("status", "").strip()

    error = validate_status_transition(feedback["status"], target_status)
    if error is not None:
        flash(error, "danger")
        return redirect(url_for("student.view_feedback", feedback_id=feedback_id))

    db = get_db()
    db.execute(
        "UPDATE feedback SET status = ?, updated_at = ? WHERE id = ?;",
        (target_status, utc_now_iso(), feedback_id),
    )
    db.commit()

    flash(f"Submission status updated to {target_status}.", "success")
    return redirect(url_for("student.view_feedback", feedback_id=feedback_id))
