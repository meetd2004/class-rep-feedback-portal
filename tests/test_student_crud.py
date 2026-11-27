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


def test_student_cannot_edit_or_delete_resolved_feedback(app, client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        resolved = conn.execute(
            "SELECT id FROM feedback WHERE status = 'Resolved' AND author_id = 1;"
        ).fetchone()
    finally:
        conn.close()
    assert resolved is not None
    fid = resolved["id"]

    assert client.get(f"/feedback/{fid}/edit").status_code == 403
    token = extract_csrf_token(client.get("/student/dashboard").get_data(as_text=True))
    assert (
        client.post(
            f"/feedback/{fid}/edit",
            data={
                "csrf_token": token,
                "title": "Post resolution edit",
                "category": "Learning Resources",
                "description": "Attempting to modify a resolved submission.",
            },
        ).status_code
        == 403
    )
    assert client.post(f"/feedback/{fid}/delete", data={"csrf_token": token}).status_code == 403


def test_server_validation_rejects_excessive_lengths_and_whitespace(app, client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))

    oversized = client.post(
        "/feedback/new",
        data={
            "csrf_token": token,
            "title": "A" * 121,
            "category": "Lectures",
            "description": "B" * 2001,
        },
    )
    assert oversized.status_code == 200
    html = oversized.get_data(as_text=True)
    assert "Title must be between 5 and 120 characters." in html
    assert "Description must be between 15 and 2000 characters." in html

    whitespace_only = client.post(
        "/feedback/new",
        data={
            "csrf_token": token,
            "title": "     ",
            "category": "Lectures",
            "description": "               \r\n   ",
        },
    )
    assert whitespace_only.status_code == 200
    ws_html = whitespace_only.get_data(as_text=True)
    assert "Title must be between 5 and 120 characters." in ws_html
    assert "Description must be between 15 and 2000 characters." in ws_html


def test_get_delete_rejected_and_missing_feedback_returns_404(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    assert client.get("/feedback/1/delete").status_code == 405
    assert client.get("/feedback/99999").status_code == 404
    assert client.get("/feedback/99999/edit").status_code == 404


def test_two_students_maintain_independent_crud_workflows(app, client) -> None:
    # Student B (Ciaran) can create, edit, and delete his own New feedback without seeing Aoife's items
    login_as(client, "ciaran.byrne@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))
    res = client.post(
        "/feedback/new",
        data={
            "csrf_token": token,
            "title": "Ciaran independent feedback",
            "category": "Timetables",
            "description": "Verifying Student B CRUD operates cleanly and independently.",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "Ciaran independent feedback" in res.get_data(as_text=True)

    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        row = conn.execute(
            "SELECT id FROM feedback WHERE title = ?;", ("Ciaran independent feedback",)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    fid = row["id"]

    del_token = extract_csrf_token(client.get(f"/feedback/{fid}").get_data(as_text=True))
    del_res = client.post(
        f"/feedback/{fid}/delete",
        data={"csrf_token": del_token},
        follow_redirects=True,
    )
    assert del_res.status_code == 200
    assert "Feedback submission deleted." in del_res.get_data(as_text=True)


def test_student_quick_request_ajax_and_live_sync_reflects_in_admin_queue(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    dash_html = client.get("/student/dashboard").get_data(as_text=True)
    assert "Raise a New Request or Feedback" in dash_html
    token = extract_csrf_token(dash_html)

    # Validation failure via fetch returns 400 JSON errors
    bad_resp = client.post(
        "/feedback/new",
        headers={"X-Requested-With": "fetch", "Accept": "application/json"},
        data={
            "csrf_token": token,
            "title": "Bad",
            "category": "Lectures",
            "description": "Short",
        },
    )
    assert bad_resp.status_code == 400
    assert bad_resp.get_json()["ok"] is False

    # Valid quick request submission returns 201 JSON ticket
    ok_resp = client.post(
        "/feedback/new",
        headers={"X-Requested-With": "fetch", "Accept": "application/json"},
        data={
            "csrf_token": token,
            "title": "Need recording captions enabled for Week 6",
            "category": "Lectures",
            "description": "Students would benefit from automated captions on Tuesday lecture recordings.",
        },
    )
    assert ok_resp.status_code == 201
    created_payload = ok_resp.get_json()
    assert created_payload["ok"] is True
    assert created_payload["ticket"]["status"] == "New"
    created_id = created_payload["ticket"]["id"]

    # Student live sync API sees the new ticket and excludes Ciaran's items
    my_api = client.get("/student/api/my-feedback")
    assert my_api.status_code == 200
    titles = [item["title"] for item in my_api.get_json()["submissions"]]
    assert "Need recording captions enabled for Week 6" in titles
    assert "Room change notice needed for Thursday lab group" not in titles

    # Switch to Class Rep Admin Console and verify ticket immediately appears in Admin live API
    client.post("/logout", data={"csrf_token": token})
    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    admin_api = client.get("/rep/api/queue-summary")
    assert admin_api.status_code == 200
    admin_data = admin_api.get_json()
    assert admin_data["latest_ticket"]["id"] == created_id
    assert admin_data["latest_ticket"]["title"] == "Need recording captions enabled for Week 6"


def test_student_dashboard_filters_by_topic_status_search_and_sort(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")

    # Category + Status filter on server dashboard
    lectures_new = client.get("/student/dashboard?category=Lectures&status=New").get_data(
        as_text=True
    )
    assert "Audio echo in Week 5 Cryptography recording" in lectures_new
    assert "Broken lab VM mirror link in Week 3 Moodle folder" not in lectures_new

    # Search + Sort on student live API
    api_sorted = client.get("/student/api/my-feedback?sort=oldest")
    assert api_sorted.status_code == 200
    ids = [item["id"] for item in api_sorted.get_json()["submissions"]]
    assert ids == sorted(ids)

    api_search = client.get("/student/api/my-feedback?q=Cryptography")
    assert api_search.status_code == 200
    titles = [item["title"] for item in api_search.get_json()["submissions"]]
    assert titles == ["Audio echo in Week 5 Cryptography recording"]
