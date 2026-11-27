"""Student workflow routes: dashboard, quick request submission, live sync API, and feedback CRUD."""

from __future__ import annotations

import sqlite3
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.db import get_db, utc_now_iso
from app.routes import render_feedback_detail
from app.security import (
    get_authorized_feedback,
    login_required,
    role_required,
    validate_feedback_input,
)

student_bp = Blueprint("student", __name__)


def _fetch_student_submissions(
    student_id: int,
    cohort: str,
    selected_category: str = "",
    selected_status: str = "",
    search_query: str = "",
    sort_by: str = "newest",
) -> list[sqlite3.Row]:
    """Return submissions authored by the given student with optional allow-listed filters."""
    escaped_q = search_query.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_pattern = f"%{escaped_q}%" if search_query else ""

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
            (SELECT COUNT(*) FROM responses AS r WHERE r.feedback_id = f.id) AS response_count,
            (
                SELECT r.message
                FROM responses AS r
                WHERE r.feedback_id = f.id
                ORDER BY r.id DESC
                LIMIT 1
            ) AS latest_reply_message,
            (
                SELECT u.full_name
                FROM responses AS r
                JOIN users AS u ON u.id = r.rep_id
                WHERE r.feedback_id = f.id
                ORDER BY r.id DESC
                LIMIT 1
            ) AS latest_reply_by,
            (
                SELECT r.created_at
                FROM responses AS r
                WHERE r.feedback_id = f.id
                ORDER BY r.id DESC
                LIMIT 1
            ) AS latest_reply_at
        FROM feedback AS f
        WHERE f.author_id = ? AND f.cohort = ?
          AND (? = '' OR f.category = ?)
          AND (? = '' OR f.status = ?)
          AND (
              ? = ''
              OR lower(f.title) LIKE ? ESCAPE '\\'
              OR lower(f.category) LIKE ? ESCAPE '\\'
              OR lower(COALESCE((
                  SELECT r.message FROM responses AS r WHERE r.feedback_id = f.id ORDER BY r.id DESC LIMIT 1
              ), '')) LIKE ? ESCAPE '\\'
          )
        ORDER BY
            CASE WHEN ? = 'status' THEN
                CASE f.status WHEN 'New' THEN 1 WHEN 'In Review' THEN 2 ELSE 3 END
            END ASC,
            CASE WHEN ? = 'oldest' THEN f.id END ASC,
            f.id DESC;
        """,
        (
            student_id,
            cohort,
            selected_category,
            selected_category,
            selected_status,
            selected_status,
            search_query,
            like_pattern,
            like_pattern,
            like_pattern,
            sort_by,
            sort_by,
        ),
    ).fetchall()


def _parse_student_filters() -> tuple[str, str, str, str]:
    """Validate and normalize student dashboard query parameters."""
    categories = current_app.config["ALLOWED_CATEGORIES"]
    statuses = current_app.config["ALLOWED_STATUSES"]

    selected_category = request.args.get("category", "").strip()
    selected_status = request.args.get("status", "").strip()
    search_query = request.args.get("q", "").strip()[:80]
    sort_by = request.args.get("sort", "newest").strip()

    if selected_category not in categories:
        selected_category = ""
    if selected_status not in statuses:
        selected_status = ""
    if sort_by not in ("newest", "oldest", "status"):
        sort_by = "newest"

    return selected_category, selected_status, search_query, sort_by


def _compute_student_counts(submissions: list[sqlite3.Row]) -> dict[str, int]:
    """Summarize submission counts by status for the student dashboard."""
    return {
        "total": len(submissions),
        "New": sum(1 for row in submissions if row["status"] == "New"),
        "In Review": sum(1 for row in submissions if row["status"] == "In Review"),
        "Resolved": sum(1 for row in submissions if row["status"] == "Resolved"),
    }


@student_bp.route("/student/dashboard")
@role_required("student")
def dashboard() -> str:
    """Display only the signed-in student's own feedback submissions and quick request UI."""
    all_submissions = _fetch_student_submissions(g.user["id"], g.user["cohort"])
    counts = _compute_student_counts(all_submissions)
    selected_category, selected_status, search_query, sort_by = _parse_student_filters()
    submissions = _fetch_student_submissions(
        g.user["id"],
        g.user["cohort"],
        selected_category,
        selected_status,
        search_query,
        sort_by,
    )
    categories = current_app.config["ALLOWED_CATEGORIES"]

    return render_template(
        "student_dashboard.html",
        submissions=submissions,
        counts=counts,
        categories=categories,
        selected_category=selected_category,
        selected_status=selected_status,
        search_query=search_query,
        sort_by=sort_by,
    )


@student_bp.route("/student/api/my-feedback")
@role_required("student")
def my_feedback_api() -> object:
    """Return live status, reply counts, and submissions scoped to the signed-in student."""
    all_submissions = _fetch_student_submissions(g.user["id"], g.user["cohort"])
    counts = _compute_student_counts(all_submissions)
    selected_category, selected_status, search_query, sort_by = _parse_student_filters()
    submissions = _fetch_student_submissions(
        g.user["id"],
        g.user["cohort"],
        selected_category,
        selected_status,
        search_query,
        sort_by,
    )

    items = [
        {
            "id": int(row["id"]),
            "title": row["title"],
            "category": row["category"],
            "status": row["status"],
            "response_count": int(row["response_count"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "latest_reply": {
                "rep_name": row["latest_reply_by"],
                "message": row["latest_reply_message"][:140],
                "created_at": row["latest_reply_at"],
            }
            if row["latest_reply_message"]
            else None,
            "view_url": url_for("student.view_feedback", feedback_id=row["id"]),
            "edit_url": url_for("student.edit_feedback", feedback_id=row["id"]),
            "delete_url": url_for("student.delete_feedback", feedback_id=row["id"]),
        }
        for row in submissions
    ]

    return jsonify({"counts": counts, "submissions": items})


@student_bp.route("/feedback/new", methods=["GET", "POST"])
@role_required("student")
def create_feedback() -> object:
    """Create a new feedback submission always initialized to status 'New'."""
    categories = current_app.config["ALLOWED_CATEGORIES"]
    form_data = {"title": "", "category": "", "description": ""}
    errors: dict[str, str] = {}
    is_fetch = request.headers.get("X-Requested-With") == "fetch"

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
            new_id = int(cursor.lastrowid)

            if is_fetch:
                return (
                    jsonify(
                        {
                            "ok": True,
                            "ticket": {
                                "id": new_id,
                                "title": form_data["title"],
                                "category": form_data["category"],
                                "status": "New",
                                "view_url": url_for("student.view_feedback", feedback_id=new_id),
                            },
                        }
                    ),
                    201,
                )

            flash("Your feedback has been submitted with status New.", "success")
            return redirect(url_for("student.view_feedback", feedback_id=new_id))

        if is_fetch:
            return jsonify({"ok": False, "errors": errors}), 400

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
    return render_feedback_detail(feedback_id)


@student_bp.route("/feedback/<int:feedback_id>/live")
@login_required
def feedback_live_api(feedback_id: int) -> object:
    """Return live status and official responses for an authorized feedback submission."""
    feedback = get_authorized_feedback(feedback_id, g.user)
    db = get_db()
    rows = db.execute(
        """
        SELECT r.id, r.message, r.created_at, u.full_name AS rep_name
        FROM responses AS r
        JOIN users AS u ON u.id = r.rep_id
        WHERE r.feedback_id = ?
        ORDER BY r.created_at ASC, r.id ASC;
        """,
        (feedback_id,),
    ).fetchall()

    return jsonify(
        {
            "id": int(feedback["id"]),
            "status": feedback["status"],
            "updated_at": feedback["updated_at"],
            "response_count": len(rows),
            "responses": [
                {
                    "id": int(row["id"]),
                    "rep_name": row["rep_name"],
                    "message": row["message"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
        }
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
            cursor = db.execute(
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
            if cursor.rowcount == 0:
                db.rollback()
                abort(403)
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
    cursor = db.execute(
        "DELETE FROM feedback WHERE id = ? AND author_id = ? AND status = 'New';",
        (feedback_id, g.user["id"]),
    )
    if cursor.rowcount == 0:
        db.rollback()
        abort(403)
    db.commit()
    flash("Feedback submission deleted.", "info")
    return redirect(url_for("student.dashboard"))
