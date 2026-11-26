"""Application configuration loaded from environment variables with secure defaults."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration with secure session and cookie defaults."""

    SECRET_KEY: str = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    PORTAL_COHORT: str = os.environ.get("PORTAL_COHORT", "MSc Cybersecurity Group B")
    DATABASE_PATH: str = os.environ.get(
        "DATABASE_PATH", str(BASE_DIR / "instance" / "feedback_portal.db")
    )

    # Session & Cookie Security (SR2)
    SESSION_COOKIE_NAME: str = "crfp_session"
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = (
        os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )
    PERMANENT_SESSION_LIFETIME: int = 3600  # 1 hour session timeout

    # CSRF Protection (SR2)
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT: int = 3600

    # Domain Constants
    ALLOWED_ROLES: tuple[str, ...] = ("student", "rep")
    ALLOWED_CATEGORIES: tuple[str, ...] = (
        "Lectures",
        "Assessments",
        "Timetables",
        "Learning Resources",
    )
    ALLOWED_STATUSES: tuple[str, ...] = ("New", "In Review", "Resolved")
    ALLOWED_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
        "New": ("In Review", "Resolved"),
        "In Review": ("Resolved",),
        "Resolved": (),
    }


class TestConfig(Config):
    """Configuration overrides for automated testing."""

    TESTING: bool = True
    SECRET_KEY: str = "test-secret-key-not-used-in-production"
    SESSION_COOKIE_SECURE: bool = False
