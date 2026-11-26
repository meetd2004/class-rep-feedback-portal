"""Tests for class rep filtering, responses, status transitions, XSS escaping, and SQLi resilience."""

from __future__ import annotations

from app.db import connect_sqlite
from tests.conftest import extract_csrf_token, login_as


def test_rep_dashboard_filters_by_category_and_status(client) -> None:
    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")

    all_html = client.get("/rep/dashboard").get_data(as_text=True)
    assert "Audio echo in Week 5 Cryptography recording" in all_html
    assert "Broken lab VM mirror link in Week 3 Moodle folder" in all_html

    filtered_html = client.get(
        "/rep/dashboard?category=Lectures&status=New"
    ).get_data(as_text=True)
    assert "Audio echo in Week 5 Cryptography recording" in filtered_html
    assert "Broken lab VM mirror link in Week 3 Moodle folder" not in filtered_html

    empty_filter_html = client.get(
        "/rep/dashboard?category=Timetables&status=Resolved"
    ).get_data(as_text=True)
    assert "No submissions match your filters" in empty_filter_html


def test_rep_response_and_status_progression_visible_to_author(app, client) -> None:
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        target = conn.execute(
            """
            SELECT f.id
            FROM feedback AS f
            JOIN users AS u ON u.id = f.author_id
            WHERE u.email = 'aoife.brennan@nci-demo.example' AND f.status = 'New';
            """
        ).fetchone()
    finally:
        conn.close()
    assert target is not None
    fid = target["id"]

    # Rep responds -> New automatically transitions to In Review
    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    detail_page = client.get(f"/feedback/{fid}")
    token = extract_csrf_token(detail_page.get_data(as_text=True))

    resp_post = client.post(
        f"/rep/feedback/{fid}/respond",
        data={
            "csrf_token": token,
            "message": "Reported the audio echo to IT Services for re-encoding.",
        },
        follow_redirects=True,
    )
    assert resp_post.status_code == 200
    assert "In Review" in resp_post.get_data(as_text=True)
    assert "Reported the audio echo to IT Services for re-encoding." in resp_post.get_data(
        as_text=True
    )

    # Rep advances status In Review -> Resolved
    token2 = extract_csrf_token(resp_post.get_data(as_text=True))
    status_post = client.post(
        f"/rep/feedback/{fid}/status",
        data={"csrf_token": token2, "status": "Resolved"},
        follow_redirects=True,
    )
    assert status_post.status_code == 200
    assert "Submission status updated to Resolved." in status_post.get_data(as_text=True)

    # Attempting invalid backward transition Resolved -> New is rejected
    token3 = extract_csrf_token(status_post.get_data(as_text=True))
    invalid_post = client.post(
        f"/rep/feedback/{fid}/status",
        data={"csrf_token": token3, "status": "New"},
        follow_redirects=True,
    )
    assert "Cannot transition status from Resolved to New." in invalid_post.get_data(as_text=True)

    # Log out rep and verify Aoife sees the response and Resolved status
    logout_token = extract_csrf_token(invalid_post.get_data(as_text=True))
    client.post("/logout", data={"csrf_token": logout_token})

    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    student_detail = client.get(f"/feedback/{fid}").get_data(as_text=True)
    assert "Reported the audio echo to IT Services for re-encoding." in student_detail
    assert "Resolved" in student_detail


def test_xss_payloads_are_html_escaped(app, client) -> None:
    xss_title = "<script>alert('xss-title')</script>"
    xss_desc = "Details with <img src=x onerror=alert('xss-body')> payload inside."

    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))
    res = client.post(
        "/feedback/new",
        data={
            "csrf_token": token,
            "title": xss_title,
            "category": "Lectures",
            "description": xss_desc,
        },
        follow_redirects=True,
    )
    html = res.get_data(as_text=True)
    assert "<script>alert('xss-title')</script>" not in html
    assert "&lt;script&gt;alert(&#39;xss-title&#39;)&lt;/script&gt;" in html
    assert "<img src=x onerror=alert('xss-body')>" not in html


def test_sql_injection_payloads_cannot_bypass_auth_or_filters(client) -> None:
    token = extract_csrf_token(client.get("/login").get_data(as_text=True))
    sqli_login = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "' OR '1'='1' --",
            "password": "' OR '1'='1",
        },
    )
    assert sqli_login.status_code == 200
    assert "Invalid email or password." in sqli_login.get_data(as_text=True)

    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    sqli_filter = client.get("/rep/dashboard?category=' OR 1=1 --&status=New")
    assert sqli_filter.status_code == 200
