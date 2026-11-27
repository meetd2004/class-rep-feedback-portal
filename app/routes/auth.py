"""Authentication and account security routes: login, CSRF logout, and password management."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for

from app.db import get_db
from app.security import (
    authenticate_user,
    clear_failed_logins,
    establish_user_session,
    hash_password,
    is_login_rate_limited,
    login_required,
    record_failed_login,
    validate_login_input,
    verify_password,
)

auth_bp = Blueprint("auth", __name__)


def _dashboard_for_role(role: str) -> str:
    """Return the dashboard endpoint corresponding to a user's role."""
    if role == "rep":
        return url_for("rep.dashboard")
    return url_for("student.dashboard")


@auth_bp.route("/")
def index() -> object:
    """Redirect authenticated users to their role dashboard or show login."""
    if g.get("user") is not None:
        return redirect(_dashboard_for_role(g.user["role"]))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> object:
    """Authenticate a user and establish a rotated, server-signed session."""
    if g.get("user") is not None:
        return redirect(_dashboard_for_role(g.user["role"]))

    email_value = ""
    error_message = None
    field_errors: dict[str, str] = {}
    status_code = 200

    if request.method == "POST":
        raw_email = request.form.get("email", "")
        raw_password = request.form.get("password", "")
        email_value, field_errors = validate_login_input(raw_email, raw_password)
        remote_addr = request.remote_addr or "unknown"

        if is_login_rate_limited(email_value or raw_email, remote_addr):
            error_message = "Too many failed sign-in attempts. Please wait a few minutes and try again."
            field_errors = {}
            status_code = 429
        elif field_errors:
            error_message = "Please fix the validation errors below before signing in."
            status_code = 400
        else:
            user = authenticate_user(email_value, raw_password)
            if user is None:
                record_failed_login(email_value, remote_addr)
                # Generic error avoids confirming whether an email exists.
                error_message = "Invalid email or password."
            else:
                clear_failed_logins(email_value, remote_addr)
                establish_user_session(user)
                flash(f"Welcome back, {user['full_name']}.", "success")
                return redirect(_dashboard_for_role(user["role"]))

    return (
        render_template(
            "login.html",
            email_value=email_value,
            error_message=error_message,
            field_errors=field_errors,
            cohort=current_app.config["PORTAL_COHORT"],
        ),
        status_code,
    )


@auth_bp.route("/account", methods=["GET"])
@login_required
def account() -> str:
    """Display signed-in user's profile and password security settings."""
    db = get_db()
    user_row = db.execute(
        "SELECT id, email, full_name, role, cohort, created_at FROM users WHERE id = ?;",
        (g.user["id"],),
    ).fetchone()
    return render_template("account.html", profile=user_row, errors={})


@auth_bp.route("/account/password", methods=["POST"])
@login_required
def change_password() -> object:
    """Allow an authenticated user to change their password after verifying the current one."""
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    db = get_db()
    user_row = db.execute(
        "SELECT id, email, full_name, password_hash, role, cohort, created_at FROM users WHERE id = ?;",
        (g.user["id"],),
    ).fetchone()

    errors: dict[str, str] = {}
    if not current_password or not verify_password(user_row["password_hash"], current_password):
        errors["current"] = "Current password is incorrect."
    if len(new_password) < 8 or len(new_password) > 128:
        errors["new"] = "New password must be between 8 and 128 characters."
    elif new_password == current_password:
        errors["new"] = "New password must differ from your current password."
    if new_password != confirm_password:
        errors["confirm"] = "Password confirmation does not match."

    if errors:
        return render_template("account.html", profile=user_row, errors=errors), 400

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?;",
        (hash_password(new_password), g.user["id"]),
    )
    db.commit()
    establish_user_session(user_row)
    flash("Your password has been updated and your session refreshed.", "success")
    return redirect(url_for("auth.account"))


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout() -> object:
    """Clear the authenticated session via POST + CSRF."""
    session.clear()
    flash("You have been signed out securely.", "info")
    return redirect(url_for("auth.login"))
