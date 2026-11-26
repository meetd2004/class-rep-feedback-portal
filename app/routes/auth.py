"""Authentication routes: role-based landing redirect, login, and CSRF-protected logout."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for

from app.security import authenticate_user, login_required

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
    """Authenticate a user and establish a fresh server-signed session."""
    if g.get("user") is not None:
        return redirect(_dashboard_for_role(g.user["role"]))

    email_value = ""
    error_message = None

    if request.method == "POST":
        email_value = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email_value or not password:
            error_message = "Please enter both your email address and password."
        else:
            user = authenticate_user(email_value, password)
            if user is None:
                # Generic error avoids confirming whether an email exists.
                error_message = "Invalid email or password."
            else:
                session.clear()
                session["user_id"] = user["id"]
                session.permanent = True
                flash(f"Welcome back, {user['full_name']}.", "success")
                return redirect(_dashboard_for_role(user["role"]))

    return render_template(
        "login.html",
        email_value=email_value,
        error_message=error_message,
        cohort=current_app.config["PORTAL_COHORT"],
    )


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout() -> object:
    """Clear the authenticated session via POST + CSRF."""
    session.clear()
    flash("You have been signed out securely.", "info")
    return redirect(url_for("auth.login"))
