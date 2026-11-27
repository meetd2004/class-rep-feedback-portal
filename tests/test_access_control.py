"""Tests for RBAC, horizontal IDOR prevention, vertical privilege escalation, and cohort isolation."""

from __future__ import annotations

from app.db import connect_sqlite
from tests.conftest import extract_csrf_token, login_as


def test_unauthenticated_routes_redirect_to_login(client) -> None:
    for path in ("/student/dashboard", "/feedback/new", "/feedback/1", "/rep/dashboard"):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/login")


def test_student_cannot_view_edit_or_delete_another_students_feedback(app, client) -> None:
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        aoife_new = conn.execute(
            """
            SELECT f.id, f.title
            FROM feedback AS f
            JOIN users AS u ON u.id = f.author_id
            WHERE u.email = 'aoife.brennan@nci-demo.example' AND f.status = 'New';
            """
        ).fetchone()
    finally:
        conn.close()
    assert aoife_new is not None
    fid = aoife_new["id"]

    # Log in as Ciaran (student 2)
    login_as(client, "ciaran.byrne@nci-demo.example", "StudentDemo!2026")
    dash_html = client.get("/student/dashboard").get_data(as_text=True)
    assert aoife_new["title"] not in dash_html

    # Horizontal IDOR attempts must be denied with 403
    assert client.get(f"/feedback/{fid}").status_code == 403
    assert client.get(f"/feedback/{fid}/live").status_code == 403
    assert client.get(f"/feedback/{fid}/edit").status_code == 403

    token = extract_csrf_token(client.get("/student/dashboard").get_data(as_text=True))
    assert (
        client.post(
            f"/feedback/{fid}/edit",
            data={
                "csrf_token": token,
                "title": "Hijacked title",
                "category": "Lectures",
                "description": "Unauthorized edit attempt by another student.",
            },
        ).status_code
        == 403
    )
    assert client.post(f"/feedback/{fid}/delete", data={"csrf_token": token}).status_code == 403


def test_student_cannot_access_rep_routes(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    assert client.get("/rep/dashboard").status_code == 403
    assert client.get("/rep/feedback/1").status_code == 403
    assert client.get("/rep/api/queue-summary").status_code == 403

    token = extract_csrf_token(client.get("/student/dashboard").get_data(as_text=True))
    assert (
        client.post(
            "/rep/feedback/1/respond",
            data={"csrf_token": token, "message": "Spoofed rep response."},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/rep/feedback/1/status",
            data={"csrf_token": token, "status": "Resolved"},
        ).status_code
        == 403
    )


def test_rep_cannot_access_student_submission_routes(client) -> None:
    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    assert client.get("/student/dashboard").status_code == 403
    assert client.get("/student/api/my-feedback").status_code == 403
    assert client.get("/feedback/new").status_code == 403

    token = extract_csrf_token(client.get("/rep/dashboard").get_data(as_text=True))
    assert (
        client.post(
            "/feedback/1/delete",
            data={"csrf_token": token},
        ).status_code
        == 403
    )


def test_out_of_cohort_rep_cannot_access_group_b_feedback(client) -> None:
    login_as(client, "groupa.rep@nci-demo.example", "RepDemo!2026")

    rep_dash = client.get("/rep/dashboard")
    assert rep_dash.status_code == 200
    assert "Audio echo in Week 5 Cryptography recording" not in rep_dash.get_data(as_text=True)

    assert client.get("/feedback/1").status_code == 403
    assert client.get("/rep/feedback/1").status_code == 403

    token = extract_csrf_token(rep_dash.get_data(as_text=True))
    assert (
        client.post(
            "/rep/feedback/1/respond",
            data={"csrf_token": token, "message": "Cross-cohort intrusion attempt."},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/rep/feedback/1/status",
            data={"csrf_token": token, "status": "Resolved"},
        ).status_code
        == 403
    )
