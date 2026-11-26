"""Tests for student feedback CRUD, server-side validation, status locks, and cascade deletes."""

from __future__ import annotations

from app.db import connect_sqlite, utc_now_iso
from tests.conftest import extract_csrf_token, login_as


def test_student_crud_lifecycle_on_new_feedback(app, client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")

    # CREATE (even if tampered status='Resolved' is sent, server forces 'New')
    form_page = client.get("/feedback/new")
    token = extract_csrf_token(form_page.get_data(as_text=True))
    create_resp = client.post(
        "/feedback/new",
        data={
            "csrf_token": token,
            "title": "Lab machine Docker permission error",
            "category": "Learning Resources",
            "description": "Students in Lab 2 cannot run container builds without permission errors.",
            "status": "Resolved",
        },
        follow_redirects=True,
    )
    assert create_resp.status_code == 200
    body = create_resp.get_data(as_text=True)
    assert "Lab machine Docker permission error" in body
    assert "New" in body

    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        created = conn.execute(
            "SELECT id, status FROM feedback WHERE title = ?;",
            ("Lab machine Docker permission error",),
        ).fetchone()
    finally:
        conn.close()

    assert created is not None
    assert created["status"] == "New"
    fid = created["id"]

    # READ on dashboard
    dash_html = client.get("/student/dashboard").get_data(as_text=True)
    assert "Lab machine Docker permission error" in dash_html

    # UPDATE while New
    edit_page = client.get(f"/feedback/{fid}/edit")
    assert edit_page.status_code == 200
    edit_token = extract_csrf_token(edit_page.get_data(as_text=True))
    update_resp = client.post(
        f"/feedback/{fid}/edit",
        data={
            "csrf_token": edit_token,
            "title": "Lab 2 Docker socket permission error",
            "category": "Learning Resources",
            "description": "Updated details: Lab 2 workstations deny access to the Docker daemon during practicals.",
        },
        follow_redirects=True,
    )
    assert update_resp.status_code == 200
    assert "Lab 2 Docker socket permission error" in update_resp.get_data(as_text=True)

    # DELETE while New
    detail_page = client.get(f"/feedback/{fid}")
    del_token = extract_csrf_token(detail_page.get_data(as_text=True))
    del_resp = client.post(
        f"/feedback/{fid}/delete",
        data={"csrf_token": del_token},
        follow_redirects=True,
    )
    assert del_resp.status_code == 200
    assert "Feedback submission deleted." in del_resp.get_data(as_text=True)

    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        deleted_row = conn.execute("SELECT id FROM feedback WHERE id = ?;", (fid,)).fetchone()
    finally:
        conn.close()
    assert deleted_row is None


def test_server_validation_rejects_invalid_category_and_short_fields(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))

    resp = client.post(
        "/feedback/new",
        data={
            "csrf_token": token,
            "title": "Hi",
            "category": "InvalidCategory",
            "description": "Too short",
        },
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Title must be between 5 and 120 characters." in html
    assert "Please select a valid feedback category." in html
    assert "Description must be between 15 and 2000 characters." in html


def test_student_cannot_edit_or_delete_non_new_feedback(app, client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        in_review = conn.execute(
            "SELECT id FROM feedback WHERE status = 'In Review' AND author_id = 1;"
        ).fetchone()
    finally:
        conn.close()
    assert in_review is not None
    fid = in_review["id"]

    assert client.get(f"/feedback/{fid}/edit").status_code == 403

    token = extract_csrf_token(client.get("/student/dashboard").get_data(as_text=True))
    assert (
        client.post(
            f"/feedback/{fid}/edit",
            data={
                "csrf_token": token,
                "title": "Attempted tampering",
                "category": "Assessments",
                "description": "Trying to edit after rep started reviewing.",
            },
        ).status_code
        == 403
    )
    assert client.post(f"/feedback/{fid}/delete", data={"csrf_token": token}).status_code == 403


def test_deleting_feedback_cascades_any_child_responses(app) -> None:
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        aoife_id = conn.execute(
            "SELECT id FROM users WHERE email = 'aoife.brennan@nci-demo.example';"
        ).fetchone()["id"]
        rep_id = conn.execute(
            "SELECT id FROM users WHERE email = 'niamh.gallagher@nci-demo.example';"
        ).fetchone()["id"]
        now = utc_now_iso()
        cur = conn.execute(
            """
            INSERT INTO feedback (author_id, cohort, title, category, description, status, created_at, updated_at)
            VALUES (?, 'MSc Cybersecurity Group B', 'Cascade test item', 'Lectures', 'Testing foreign key cascade deletion behavior.', 'New', ?, ?);
            """,
            (aoife_id, now, now),
        )
        fid = cur.lastrowid
        conn.execute(
            "INSERT INTO responses (feedback_id, rep_id, message, created_at) VALUES (?, ?, 'Cascade child', ?);",
            (fid, rep_id, now),
        )
        conn.commit()

        conn.execute("DELETE FROM feedback WHERE id = ?;", (fid,))
        conn.commit()
        remaining = conn.execute(
            "SELECT COUNT(*) AS cnt FROM responses WHERE feedback_id = ?;", (fid,)
        ).fetchone()["cnt"]
    finally:
        conn.close()

    assert remaining == 0
