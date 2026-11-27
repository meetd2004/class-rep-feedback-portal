"""Tests for authentication, Argon2id password hashing, session flags, headers, and CSRF."""

from __future__ import annotations

from app.db import connect_sqlite
from tests.conftest import extract_csrf_token, login_as


def test_passwords_are_stored_as_argon2id_hashes(app) -> None:
    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        rows = conn.execute("SELECT email, password_hash FROM users;").fetchall()
    finally:
        conn.close()

    assert len(rows) >= 3
    for row in rows:
        assert row["password_hash"].startswith("$argon2id$")
        assert "StudentDemo!2026" not in row["password_hash"]
        assert "RepDemo!2026" not in row["password_hash"]


def test_login_redirects_by_role_and_sets_secure_session_flags(client) -> None:
    resp_student = login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    assert resp_student.status_code == 302
    assert resp_student.headers["Location"].endswith("/student/dashboard")

    set_cookie = resp_student.headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie
    assert "SameSite=Lax" in set_cookie

    dash = client.get("/student/dashboard")
    assert dash.status_code == 200
    assert dash.headers.get("X-Content-Type-Options") == "nosniff"
    assert dash.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in dash.headers.get("Content-Security-Policy", "")


def test_rep_login_redirects_to_rep_dashboard(client) -> None:
    resp_rep = login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")
    assert resp_rep.status_code == 302
    assert resp_rep.headers["Location"].endswith("/rep/dashboard")


def test_login_uses_generic_error_for_bad_email_or_password(client) -> None:
    login_page = client.get("/login")
    token = extract_csrf_token(login_page.get_data(as_text=True))

    wrong_pass = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "aoife.brennan@nci-demo.example",
            "password": "WrongPassword123",
        },
    )
    wrong_user = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "nobody@nci-demo.example",
            "password": "WrongPassword123",
        },
    )
    assert wrong_pass.status_code == 200
    assert wrong_user.status_code == 200
    assert "Invalid email or password." in wrong_pass.get_data(as_text=True)
    assert "Invalid email or password." in wrong_user.get_data(as_text=True)


def test_csrf_protection_blocks_forged_requests(client) -> None:
    # Missing CSRF token on login
    res_login = client.post(
        "/login",
        data={"email": "aoife.brennan@nci-demo.example", "password": "StudentDemo!2026"},
    )
    assert res_login.status_code == 400

    # Sign in legitimately, then submit state-changing requests without CSRF token
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    res_create = client.post(
        "/feedback/new",
        data={
            "title": "Valid Title Without Token",
            "category": "Lectures",
            "description": "This should fail CSRF verification on the server.",
        },
    )
    assert res_create.status_code == 400

    res_logout = client.post("/logout")
    assert res_logout.status_code == 400


def test_logout_clears_session(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    dash = client.get("/student/dashboard")
    token = extract_csrf_token(dash.get_data(as_text=True))

    res_logout = client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    assert res_logout.status_code == 302
    assert res_logout.headers["Location"].endswith("/login")

    after_logout = client.get("/student/dashboard", follow_redirects=False)
    assert after_logout.status_code == 302
    assert after_logout.headers["Location"].endswith("/login")


def test_authenticated_users_redirect_from_root_and_login_by_role(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    for path in ("/", "/login"):
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/student/dashboard")

    dash = client.get("/student/dashboard")
    assert "no-store" in dash.headers.get("Cache-Control", "")


def test_get_logout_is_rejected(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    assert client.get("/logout").status_code == 405


def test_idle_session_timeout_invalidates_session(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    with client.session_transaction() as sess:
        sess["last_seen_at"] = 1  # Force expired idle timestamp

    resp = client.get("/student/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_login_rate_limiting_blocks_excessive_failed_attempts(client) -> None:
    token = extract_csrf_token(client.get("/login").get_data(as_text=True))
    for _ in range(5):
        resp = client.post(
            "/login",
            data={
                "csrf_token": token,
                "email": "aoife.brennan@nci-demo.example",
                "password": "WrongPassword123",
            },
        )
        assert resp.status_code == 200

    throttled = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "aoife.brennan@nci-demo.example",
            "password": "StudentDemo!2026",
        },
    )
    assert throttled.status_code == 429
    assert "Too many failed sign-in attempts" in throttled.get_data(as_text=True)


def test_account_profile_and_password_change_flow(client) -> None:
    assert client.get("/account", follow_redirects=False).status_code == 302

    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    acc_page = client.get("/account")
    assert acc_page.status_code == 200
    assert "Aoife Brennan" in acc_page.get_data(as_text=True)
    token = extract_csrf_token(acc_page.get_data(as_text=True))

    # Wrong current password or mismatched confirmation returns 400
    bad_pw = client.post(
        "/account/password",
        data={
            "csrf_token": token,
            "current_password": "WrongPassword",
            "new_password": "NewSecurePassword!2026",
            "confirm_password": "DifferentPassword!2026",
        },
    )
    assert bad_pw.status_code == 400
    bad_html = bad_pw.get_data(as_text=True)
    assert "Current password is incorrect." in bad_html
    assert "Password confirmation does not match." in bad_html

    # Valid password change succeeds and authenticates with new password
    ok_pw = client.post(
        "/account/password",
        data={
            "csrf_token": token,
            "current_password": "StudentDemo!2026",
            "new_password": "UpdatedDemoPass!2026",
            "confirm_password": "UpdatedDemoPass!2026",
        },
        follow_redirects=True,
    )
    assert ok_pw.status_code == 200
    assert "Your password has been updated" in ok_pw.get_data(as_text=True)

    logout_token = extract_csrf_token(ok_pw.get_data(as_text=True))
    client.post("/logout", data={"csrf_token": logout_token})

    relogin = login_as(client, "aoife.brennan@nci-demo.example", "UpdatedDemoPass!2026")
    assert relogin.status_code == 302
    assert relogin.headers["Location"].endswith("/student/dashboard")


def test_login_data_validation_rejects_malformed_email_and_out_of_bounds_password(client) -> None:
    token = extract_csrf_token(client.get("/login").get_data(as_text=True))

    bad_email = client.post(
        "/login",
        data={"csrf_token": token, "email": "not-an-email", "password": "ValidLengthPassword"},
    )
    assert bad_email.status_code == 400
    assert "Enter a valid email address" in bad_email.get_data(as_text=True)

    too_short_pw = client.post(
        "/login",
        data={"csrf_token": token, "email": "aoife.brennan@nci-demo.example", "password": "short"},
    )
    assert too_short_pw.status_code == 400
    assert "must be between 8 and 128 characters" in too_short_pw.get_data(as_text=True)

    oversized_pw = client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": "aoife.brennan@nci-demo.example",
            "password": "X" * 500,
        },
    )
    assert oversized_pw.status_code == 400
    assert "must be between 8 and 128 characters" in oversized_pw.get_data(as_text=True)
