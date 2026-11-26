"""Authentication routes: role-based landing redirect, login throttling, and CSRF logout."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for

from app.security import (
    authenticate_user,
    clear_failed_logins,
    establish_user_session,
    is_login_rate_limited,
    login_required,
    record_failed_login,
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
    status_code = 200

    if request.method == "POST":
        email_value = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remote_addr = request.remote_addr or "unknown"

        if is_login_rate_limited(email_value, remote_addr):
            error_message = "Too many failed sign-in attempts. Please wait a few minutes and try again."
            status_code = 429
        elif not email_value or not password:
            error_message = "Please enter both your email address and password."
        else:
            user = authenticate_user(email_value, password)
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
            cohort=current_app.config["PORTAL_COHORT"],
        ),
        status_code,
    )


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout() -> object:
    """Clear the authenticated session via POST + CSRF."""
    session.clear()
    flash("You have been signed out securely.", "info")
    return redirect(url_for("auth.login"))
