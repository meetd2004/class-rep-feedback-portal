"""Shared pytest fixtures and helpers for functional and security tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.config import TestConfig
from app.db import connect_sqlite, init_db_and_seed, utc_now_iso
from app.security import hash_password

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


def extract_csrf_token(html: str) -> str:
    """Extract the Flask-WTF CSRF token from rendered HTML."""
    match = CSRF_RE.search(html)
    assert match is not None, "Expected csrf_token hidden input in rendered HTML"
    return match.group(1)


def login_as(client: FlaskClient, email: str, password: str):
    """Sign into the portal using a real CSRF token."""
    login_page = client.get("/login")
    token = extract_csrf_token(login_page.get_data(as_text=True))
    return client.post(
        "/login",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    """Provide an isolated Flask app backed by a temporary seeded SQLite database."""
    db_file = tmp_path / "test_portal.db"
    test_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": TestConfig.SECRET_KEY,
            "DATABASE_PATH": str(db_file),
            "SESSION_COOKIE_SECURE": False,
            "WTF_CSRF_ENABLED": True,
        }
    )
    init_db_and_seed(test_app, hash_password)

    # Add an out-of-cohort Group A rep to verify cohort isolation boundaries.
    conn = connect_sqlite(db_file)
    try:
        conn.execute(
            """
            INSERT INTO users (email, full_name, password_hash, role, cohort, created_at)
            VALUES (?, ?, ?, 'rep', ?, ?);
            """,
            (
                "groupa.rep@nci-demo.example",
                "Declan Murphy",
                hash_password("RepDemo!2026"),
                "MSc Cybersecurity Group A",
                utc_now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return test_app


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Unauthenticated Flask test client."""
    return app.test_client()
