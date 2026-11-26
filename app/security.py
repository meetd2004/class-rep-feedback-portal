"""Security controls: password hashing, authentication guards, RBAC, ownership, and validation."""

from __future__ import annotations

import secrets
import sqlite3
import time
from functools import wraps
from typing import Callable, TypeVar

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask import abort, current_app, flash, g, redirect, session, url_for

from app.db import get_db

SESSION_IDLE_TIMEOUT_SECONDS = 1800  # 30-minute idle timeout
LOGIN_WINDOW_SECONDS = 300  # 5-minute sliding rate-limit window
MAX_FAILED_LOGINS = 5

F = TypeVar("F", bound=Callable[..., object])

_PASSWORD_HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
)
# Dummy Argon2id hash used when an email does not exist to keep login timing uniform.
_DUMMY_HASH = _PASSWORD_HASHER.hash("dummy-timing-equalizer-password")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _PASSWORD_HASHER.hash(plain_password)


def verify_password(stored_hash: str, candidate_password: str) -> bool:
    """Verify a candidate password against an Argon2id hash without raising."""
    try:
        return bool(_PASSWORD_HASHER.verify(stored_hash, candidate_password))
    except (VerifyMismatchError, InvalidHashError):
        return False


def authenticate_user(email: str, password: str) -> sqlite3.Row | None:
    """Authenticate by email and password using parameterised query and Argon2id."""
    normalized_email = email.strip().lower()
    db = get_db()
    user = db.execute(
        """
        SELECT id, email, full_name, password_hash, role, cohort
        FROM users
        WHERE lower(email) = ?;
        """,
        (normalized_email,),
    ).fetchone()

    if user is None:
        verify_password(_DUMMY_HASH, password)
        return None

    if not verify_password(user["password_hash"], password):
        return None

    return user


def _attempt_store() -> dict[str, list[float]]:
    """Return the per-app failed-login attempt store."""
    store = current_app.extensions.setdefault("login_attempts", {})
    return store  # type: ignore[return-value]


def is_login_rate_limited(identifier: str, remote_addr: str) -> bool:
    """Return True when failed login attempts exceed the threshold in the sliding window."""
    key = f"{remote_addr}|{identifier.strip().lower()}"
    now = time.time()
    store = _attempt_store()
    recent = [ts for ts in store.get(key, []) if now - ts < LOGIN_WINDOW_SECONDS]
    if recent:
        store[key] = recent
    else:
        store.pop(key, None)
    return len(recent) >= MAX_FAILED_LOGINS


def record_failed_login(identifier: str, remote_addr: str) -> None:
    """Record a failed login timestamp for throttling."""
    key = f"{remote_addr}|{identifier.strip().lower()}"
    now = time.time()
    store = _attempt_store()
    recent = [ts for ts in store.get(key, []) if now - ts < LOGIN_WINDOW_SECONDS]
    recent.append(now)
    store[key] = recent


def clear_failed_logins(identifier: str, remote_addr: str) -> None:
    """Clear recorded failed login attempts upon successful sign-in."""
    key = f"{remote_addr}|{identifier.strip().lower()}"
    _attempt_store().pop(key, None)


def establish_user_session(user: sqlite3.Row) -> None:
    """Rotate and populate a clean server-signed session after authentication."""
    now = int(time.time())
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["session_id"] = secrets.token_urlsafe(16)
    session["login_at"] = now
    session["last_seen_at"] = now
    session.permanent = True


def load_current_user() -> None:
    """Load the authenticated user and enforce session integrity and idle timeout."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return

    now = int(time.time())
    last_seen = session.get("last_seen_at")
    if isinstance(last_seen, (int, float)) and (now - int(last_seen)) > SESSION_IDLE_TIMEOUT_SECONDS:
        session.clear()
        g.user = None
        return

    db = get_db()
    user = db.execute(
        "SELECT id, email, full_name, role, cohort FROM users WHERE id = ?;",
        (user_id,),
    ).fetchone()

    if user is None or (session.get("role") is not None and session.get("role") != user["role"]):
        session.clear()
        g.user = None
        return

    session["last_seen_at"] = now
    g.user = user


def login_required(view: F) -> F:
    """Require an authenticated session before accessing a route."""

    @wraps(view)
    def wrapped_view(*args: object, **kwargs: object) -> object:
        if g.get("user") is None:
            flash("Please sign in to access the portal.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view  # type: ignore[return-value]


def role_required(*allowed_roles: str) -> Callable[[F], F]:
    """Enforce role-based access control on the server."""

    def decorator(view: F) -> F:
        @wraps(view)
        def wrapped_view(*args: object, **kwargs: object) -> object:
            user = g.get("user")
            if user is None:
                flash("Please sign in to access the portal.", "warning")
                return redirect(url_for("auth.login"))
            if user["role"] not in allowed_roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view  # type: ignore[return-value]

    return decorator


def get_authorized_feedback(
    feedback_id: int,
    user: sqlite3.Row,
    *,
    require_owner_new: bool = False,
    require_rep_cohort: bool = False,
) -> sqlite3.Row:
    """Fetch a feedback record and enforce cohort, role, ownership, and status rules."""
    db = get_db()
    feedback = db.execute(
        """
        SELECT
            f.id,
            f.author_id,
            f.cohort,
            f.title,
            f.category,
            f.description,
            f.status,
            f.created_at,
            f.updated_at,
            u.full_name AS author_name,
            u.email AS author_email
        FROM feedback AS f
        JOIN users AS u ON u.id = f.author_id
        WHERE f.id = ?;
        """,
        (feedback_id,),
    ).fetchone()

    if feedback is None:
        abort(404)

    # Cohort boundary check (Group B isolation)
    if feedback["cohort"] != user["cohort"]:
        abort(403)

    if require_owner_new:
        if user["role"] != "student" or feedback["author_id"] != user["id"]:
            abort(403)
        if feedback["status"] != "New":
            abort(403)
        return feedback

    if require_rep_cohort:
        if user["role"] != "rep":
            abort(403)
        return feedback

    # General read rule: author student OR assigned group rep
    if user["role"] == "student" and feedback["author_id"] != user["id"]:
        abort(403)
    if user["role"] not in ("student", "rep"):
        abort(403)

    return feedback


def _normalize_text(value: str) -> str:
    """Strip NUL bytes, normalise CRLF newlines, and trim outer whitespace."""
    return value.replace("\x00", "").replace("\r\n", "\n").strip()


def validate_feedback_input(
    title: str,
    category: str,
    description: str,
    allowed_categories: tuple[str, ...] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Validate and normalise feedback submission fields on the server."""
    categories = allowed_categories or current_app.config["ALLOWED_CATEGORIES"]
    cleaned = {
        "title": _normalize_text(title),
        "category": _normalize_text(category),
        "description": _normalize_text(description),
    }
    errors: dict[str, str] = {}

    if len(cleaned["title"]) < 5 or len(cleaned["title"]) > 120:
        errors["title"] = "Title must be between 5 and 120 characters."

    if cleaned["category"] not in categories:
        errors["category"] = "Please select a valid feedback category."

    if len(cleaned["description"]) < 15 or len(cleaned["description"]) > 2000:
        errors["description"] = "Description must be between 15 and 2000 characters."

    return cleaned, errors


def validate_response_input(message: str) -> tuple[str, str | None]:
    """Validate class rep response text on the server."""
    cleaned = _normalize_text(message)
    if len(cleaned) < 5 or len(cleaned) > 1500:
        return cleaned, "Response must be between 5 and 1500 characters."
    return cleaned, None


def validate_status_transition(
    current_status: str,
    target_status: str,
    transitions: dict[str, tuple[str, ...]] | None = None,
) -> str | None:
    """Validate allowed status workflow transitions (New -> In Review -> Resolved)."""
    allowed_map = transitions or current_app.config["ALLOWED_STATUS_TRANSITIONS"]
    if target_status not in current_app.config["ALLOWED_STATUSES"]:
        return "Invalid status selected."
    if target_status == current_status:
        return "Submission is already in that status."
    if target_status not in allowed_map.get(current_status, ()):
        return f"Cannot transition status from {current_status} to {target_status}."
    return None
