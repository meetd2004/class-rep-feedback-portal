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

    live_json = client.get(f"/feedback/{fid}/live").get_json()
    assert live_json["status"] == "Resolved"
    assert live_json["response_count"] >= 1
    assert any(
        r["message"] == "Reported the audio echo to IT Services for re-encoding."
        for r in live_json["responses"]
    )

    my_feed = client.get("/student/api/my-feedback").get_json()
    matched = [item for item in my_feed["submissions"] if item["id"] == fid][0]
    assert matched["latest_reply"]["rep_name"] == "Niamh Gallagher"
    assert "Reported the audio echo" in matched["latest_reply"]["message"]


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

    sqli_search = client.get("/rep/dashboard?q=' OR 1=1 --")
    assert sqli_search.status_code == 200
    assert "No submissions match your filters" in sqli_search.get_data(as_text=True)


def test_rep_dashboard_search_filters_and_escapes_wildcards(client) -> None:
    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")

    match_html = client.get("/rep/dashboard?q=Cryptography").get_data(as_text=True)
    assert "Audio echo in Week 5 Cryptography recording" in match_html
    assert "Broken lab VM mirror link in Week 3 Moodle folder" not in match_html

    # Literal '%' must not match everything as an unescaped SQL LIKE wildcard
    wildcard_html = client.get("/rep/dashboard?q=%").get_data(as_text=True)
    assert "No submissions match your filters" in wildcard_html


def test_rep_response_validation_rejects_short_or_empty_messages(app, client) -> None:
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        target = conn.execute(
            "SELECT id FROM feedback WHERE status = 'New' LIMIT 1;"
        ).fetchone()
    finally:
        conn.close()
    assert target is not None
    fid = target["id"]

    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    token = extract_csrf_token(client.get(f"/feedback/{fid}").get_data(as_text=True))

    res = client.post(
        f"/rep/feedback/{fid}/respond",
        data={"csrf_token": token, "message": "Ok"},
        follow_redirects=True,
    )
    assert "Response must be between 5 and 1500 characters." in res.get_data(as_text=True)

    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        row = conn.execute("SELECT status FROM feedback WHERE id = ?;", (fid,)).fetchone()
    finally:
        conn.close()
    assert row["status"] == "New"


def test_rep_explicit_status_flow_and_xss_escaped_replies(app, client) -> None:
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        target = conn.execute(
            """
            SELECT f.id
            FROM feedback AS f
            JOIN users AS u ON u.id = f.author_id
            WHERE u.email = 'ciaran.byrne@nci-demo.example' AND f.status = 'New';
            """
        ).fetchone()
    finally:
        conn.close()
    assert target is not None
    fid = target["id"]

    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    token = extract_csrf_token(client.get(f"/feedback/{fid}").get_data(as_text=True))

    # Move New -> In Review explicitly first
    r1 = client.post(
        f"/rep/feedback/{fid}/status",
        data={"csrf_token": token, "status": "In Review"},
        follow_redirects=True,
    )
    assert "Submission status updated to In Review." in r1.get_data(as_text=True)

    # Post reply containing script tag -> must render HTML-escaped
    token2 = extract_csrf_token(r1.get_data(as_text=True))
    r2 = client.post(
        f"/rep/feedback/{fid}/respond",
        data={"csrf_token": token2, "message": "Update <script>alert('rep')</script> confirmed."},
        follow_redirects=True,
    )
    html = r2.get_data(as_text=True)
    assert "<script>alert('rep')</script>" not in html
    assert "&lt;script&gt;alert(&#39;rep&#39;)&lt;/script&gt;" in html

    # GET on rep POST endpoints is rejected
    assert client.get(f"/rep/feedback/{fid}/respond").status_code == 405
    assert client.get(f"/rep/feedback/{fid}/status").status_code == 405


def test_student_and_rep_render_distinct_interfaces(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    student_html = client.get("/student/dashboard").get_data(as_text=True)
    assert "theme-student" in student_html
    assert "Student Feedback Portal" in student_html
    assert "RepDesk Admin" not in student_html

    logout_token = extract_csrf_token(student_html)
    client.post("/logout", data={"csrf_token": logout_token})

    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    rep_html = client.get("/rep/dashboard").get_data(as_text=True)
    assert "theme-admin" in rep_html
    assert "RepDesk Admin" in rep_html
    assert "Representative Management Console" in rep_html

    rep_detail_html = client.get("/rep/feedback/1").get_data(as_text=True)
    assert "admin-triage-grid" in rep_detail_html


def test_student_submission_raises_live_ticket_in_admin_queue_and_sidebar_views(app, client) -> None:
    # Student submits a brand new feedback item
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))
    client.post(
        "/feedback/new",
        data={
            "csrf_token": token,
            "title": "Projector HDMI cable faulty in Lab 4",
            "category": "Learning Resources",
            "description": "The HDMI adapter in Lab 4 disconnects intermittently during tutorials.",
        },
        follow_redirects=True,
    )
    logout_tok = extract_csrf_token(client.get("/student/dashboard").get_data(as_text=True))
    client.post("/logout", data={"csrf_token": logout_tok})

    # Rep signs into Admin Console and verifies live JSON sync, sidebar counts, and quick triage
    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    api_resp = client.get("/rep/api/queue-summary")
    assert api_resp.status_code == 200
    payload = api_resp.get_json()
    assert payload["latest_ticket"]["title"] == "Projector HDMI cable faulty in Lab 4"
    assert payload["counts"]["New"] >= 3
    assert payload["counts"]["categories"]["Learning Resources"] >= 2

    # All sidebar Queue Views & Topic links return 200 and show matching tickets
    for path in (
        "/rep/dashboard?status=New",
        "/rep/dashboard?status=In%20Review",
        "/rep/dashboard?status=Resolved",
        "/rep/dashboard?category=Lectures",
        "/rep/dashboard?category=Assessments",
        "/rep/dashboard?category=Timetables",
        "/rep/dashboard?category=Learning%20Resources",
    ):
        assert client.get(path).status_code == 200

    # Quick Start Review from dashboard transitions ticket to In Review
    new_id = payload["latest_ticket"]["id"]
    dash_html = client.get("/rep/dashboard?status=New").get_data(as_text=True)
    assert "Projector HDMI cable faulty in Lab 4" in dash_html
    dash_token = extract_csrf_token(dash_html)
    triage_resp = client.post(
        f"/rep/feedback/{new_id}/status",
        data={"csrf_token": dash_token, "status": "In Review", "next": "dashboard"},
        follow_redirects=True,
    )
    assert triage_resp.status_code == 200
    assert "Submission status updated to In Review." in triage_resp.get_data(as_text=True)
