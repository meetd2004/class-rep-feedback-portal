"""Class rep workflow routes: filtered cohort queue, live sync API, responses, and status progression."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from app.db import get_db, utc_now_iso
from app.routes import render_feedback_detail
from app.security import (
    get_authorized_feedback,
    role_required,
    validate_response_input,
    validate_status_transition,
)

rep_bp = Blueprint("rep", __name__, url_prefix="/rep")


def _escape_like(value: str) -> str:
    """Escape SQL LIKE wildcards so user search terms match literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_rep_queue_counts(cohort: str) -> dict[str, Any]:
    """Return status and category counts scoped strictly to the given cohort."""
    db = get_db()
    categories = current_app.config["ALLOWED_CATEGORIES"]
    counts: dict[str, Any] = {
        "total": 0,
        "New": 0,
        "In Review": 0,
        "Resolved": 0,
        "categories": {cat: 0 for cat in categories},
    }

    status_rows = db.execute(
        "SELECT status, COUNT(*) AS cnt FROM feedback WHERE cohort = ? GROUP BY status;",
        (cohort,),
    ).fetchall()
    for row in status_rows:
        counts[row["status"]] = int(row["cnt"])
        counts["total"] += int(row["cnt"])

    cat_rows = db.execute(
        "SELECT category, COUNT(*) AS cnt FROM feedback WHERE cohort = ? GROUP BY category;",
        (cohort,),
    ).fetchall()
    for row in cat_rows:
        if row["category"] in counts["categories"]:
            counts["categories"][row["category"]] = int(row["cnt"])

    return counts


def _parse_queue_filters() -> tuple[str, str, str]:
    """Read and allow-list validate category, status, and search query filters."""
    categories = current_app.config["ALLOWED_CATEGORIES"]
    statuses = current_app.config["ALLOWED_STATUSES"]

    selected_category = request.args.get("category", "").strip()
    selected_status = request.args.get("status", "").strip()
    search_query = request.args.get("q", "").strip()[:80]

    if selected_category not in categories:
        selected_category = ""
    if selected_status not in statuses:
        selected_status = ""

    return selected_category, selected_status, search_query


def _fetch_queue_submissions(
    cohort: str,
    selected_category: str,
    selected_status: str,
    search_query: str,
) -> list[sqlite3.Row]:
    """Fetch filtered feedback rows for the assigned cohort using parameterised SQL."""
    like_pattern = f"%{_escape_like(search_query.lower())}%" if search_query else ""
    db = get_db()
    return db.execute(
        """
        SELECT
            f.id,
            f.title,
            f.category,
            f.status,
            f.created_at,
            f.updated_at,
            u.full_name AS author_name,
            (SELECT COUNT(*) FROM responses AS r WHERE r.feedback_id = f.id) AS response_count,
            (SELECT COUNT(*) FROM attachments AS a WHERE a.feedback_id = f.id) AS attachment_count
        FROM feedback AS f
        JOIN users AS u ON u.id = f.author_id
        WHERE f.cohort = ?
          AND (? = '' OR f.category = ?)
          AND (? = '' OR f.status = ?)
          AND (
              ? = ''
              OR lower(f.title) LIKE ? ESCAPE '\\'
              OR lower(f.description) LIKE ? ESCAPE '\\'
              OR lower(u.full_name) LIKE ? ESCAPE '\\'
          )
        ORDER BY
            CASE f.status
                WHEN 'New' THEN 1
                WHEN 'In Review' THEN 2
                ELSE 3
            END,
            f.id DESC;
        """,
        (
            cohort,
            selected_category,
            selected_category,
            selected_status,
            selected_status,
            search_query,
            like_pattern,
            like_pattern,
            like_pattern,
        ),
    ).fetchall()


@rep_bp.route("/dashboard")
@role_required("rep")
def dashboard() -> str:
    """Display all feedback for the rep's assigned cohort with safe filters and search."""
    categories = current_app.config["ALLOWED_CATEGORIES"]
    statuses = current_app.config["ALLOWED_STATUSES"]
    selected_category, selected_status, search_query = _parse_queue_filters()

    counts = get_rep_queue_counts(g.user["cohort"])
    submissions = _fetch_queue_submissions(
        g.user["cohort"], selected_category, selected_status, search_query
    )
    latest_ticket_id = max((int(row["id"]) for row in submissions), default=0)

    return render_template(
        "rep_dashboard.html",
        submissions=submissions,
        categories=categories,
        statuses=statuses,
        selected_category=selected_category,
        selected_status=selected_status,
        search_query=search_query,
        counts=counts,
        latest_ticket_id=latest_ticket_id,
    )


@rep_bp.route("/api/queue-summary")
@role_required("rep")
def queue_summary_api() -> object:
    """Return live cohort ticket counts and filtered queue items for interactive polling."""
    selected_category, selected_status, search_query = _parse_queue_filters()
    cohort = g.user["cohort"]
    counts = get_rep_queue_counts(cohort)
    submissions = _fetch_queue_submissions(
        cohort, selected_category, selected_status, search_query
    )

    db = get_db()
    latest_row = db.execute(
        """
        SELECT f.id, f.title, f.category, f.status, u.full_name AS author_name
        FROM feedback AS f
        JOIN users AS u ON u.id = f.author_id
        WHERE f.cohort = ?
        ORDER BY f.id DESC
        LIMIT 1;
        """,
        (cohort,),
    ).fetchone()

    tickets = [
        {
            "id": int(row["id"]),
            "title": row["title"],
            "author_name": row["author_name"],
            "category": row["category"],
            "status": row["status"],
            "response_count": int(row["response_count"]),
            "attachment_count": int(row["attachment_count"]),
            "updated_at": row["updated_at"],
            "detail_url": url_for("rep.view_feedback", feedback_id=row["id"]),
            "status_url": url_for("rep.update_status", feedback_id=row["id"]),
        }
        for row in submissions
    ]

    return jsonify(
        {
            "counts": counts,
            "latest_ticket": {
                "id": int(latest_row["id"]),
                "title": latest_row["title"],
                "category": latest_row["category"],
                "status": latest_row["status"],
                "author_name": latest_row["author_name"],
                "detail_url": url_for("rep.view_feedback", feedback_id=latest_row["id"]),
            }
            if latest_row
            else None,
            "tickets": tickets,
        }
    )


@rep_bp.route("/feedback/<int:feedback_id>")
@role_required("rep")
def view_feedback(feedback_id: int) -> str:
    """Admin-side detail view for reviewing and responding to a cohort submission."""
    return render_feedback_detail(feedback_id, require_rep_cohort=True)


@rep_bp.route("/feedback/<int:feedback_id>/respond", methods=["POST"])
@role_required("rep")
def add_response(feedback_id: int) -> object:
    """Post an official class rep response and optionally advance submission status."""
    feedback = get_authorized_feedback(feedback_id, g.user, require_rep_cohort=True)
    cleaned_message, error = validate_response_input(request.form.get("message", ""))

    if error is not None:
        flash(error, "danger")
        return redirect(url_for("rep.view_feedback", feedback_id=feedback_id))

    requested_status = request.form.get("target_status", "").strip()
    if requested_status:
        if requested_status == feedback["status"] and feedback["status"] != "New":
            new_status = feedback["status"]
        else:
            status_error = validate_status_transition(feedback["status"], requested_status)
            if status_error is not None:
                flash(status_error, "danger")
                return redirect(url_for("rep.view_feedback", feedback_id=feedback_id))
            new_status = requested_status
    else:
        # Automatically move 'New' -> 'In Review' once a rep responds so the item is locked from student edits/deletion.
        new_status = "In Review" if feedback["status"] == "New" else feedback["status"]

    now = utc_now_iso()
    db = get_db()
    db.execute(
        """
        INSERT INTO responses (feedback_id, rep_id, message, created_at)
        VALUES (?, ?, ?, ?);
        """,
        (feedback_id, g.user["id"], cleaned_message, now),
    )

    cursor = db.execute(
        "UPDATE feedback SET status = ?, updated_at = ? WHERE id = ? AND cohort = ?;",
        (new_status, now, feedback_id, g.user["cohort"]),
    )
    if cursor.rowcount == 0:
        db.rollback()
        abort(403)
    db.commit()

    if new_status != feedback["status"]:
        flash(
            f"Response posted to {feedback['author_name']} and status updated to {new_status}.",
            "success",
        )
    else:
        flash(f"Response posted to {feedback['author_name']}.", "success")

    return redirect(url_for("rep.view_feedback", feedback_id=feedback_id))


@rep_bp.route("/feedback/<int:feedback_id>/status", methods=["POST"])
@role_required("rep")
def update_status(feedback_id: int) -> object:
    """Advance feedback status along the allowed workflow (New -> In Review -> Resolved)."""
    feedback = get_authorized_feedback(feedback_id, g.user, require_rep_cohort=True)
    target_status = request.form.get("status", "").strip()

    error = validate_status_transition(feedback["status"], target_status)
    if error is not None:
        flash(error, "danger")
        return redirect(url_for("rep.view_feedback", feedback_id=feedback_id))

    db = get_db()
    cursor = db.execute(
        "UPDATE feedback SET status = ?, updated_at = ? WHERE id = ? AND cohort = ? AND status = ?;",
        (target_status, utc_now_iso(), feedback_id, g.user["cohort"], feedback["status"]),
    )
    if cursor.rowcount == 0:
        db.rollback()
        abort(409)
    db.commit()

    flash(f"Submission status updated to {target_status}.", "success")
    if request.form.get("next") == "dashboard":
        return redirect(url_for("rep.dashboard"))
    return redirect(url_for("rep.view_feedback", feedback_id=feedback_id))
