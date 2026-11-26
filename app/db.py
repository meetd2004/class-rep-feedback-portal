"""Database connection, migration runner, and fictional seed data helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def utc_now_iso() -> str:
    """Return the current UTC timestamp formatted consistently for storage."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def connect_sqlite(database_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with row mapping and foreign-key enforcement."""
    db_path = Path(database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_db() -> sqlite3.Connection:
    """Return the per-request database connection stored on Flask's g object."""
    if "db" not in g:
        g.db = connect_sqlite(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exception: BaseException | None = None) -> None:
    """Close the per-request database connection during app teardown."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def run_migrations(database_path: str | Path) -> list[str]:
    """Apply pending SQL migrations in lexical order and return applied versions."""
    conn = connect_sqlite(database_path)
    applied_now: list[str] = []
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            """
        )
        rows = conn.execute("SELECT version FROM schema_migrations;").fetchall()
        already_applied = {row["version"] for row in rows}

        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = sql_file.name
            if version in already_applied:
                continue
            sql_script = sql_file.read_text(encoding="utf-8")
            conn.executescript(sql_script)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                (version, utc_now_iso()),
            )
            conn.commit()
            applied_now.append(version)
    finally:
        conn.close()
    return applied_now


def seed_demo_data(database_path: str | Path, hash_password_fn: Any) -> bool:
    """Populate fictional Group B accounts, feedback, and responses if empty."""
    conn = connect_sqlite(database_path)
    try:
        existing_count = conn.execute("SELECT COUNT(*) AS cnt FROM users;").fetchone()["cnt"]
        if existing_count > 0:
            return False

        now = utc_now_iso()
        cohort = "MSc Cybersecurity Group B"

        demo_users = [
            (
                "aoife.brennan@nci-demo.example",
                "Aoife Brennan",
                hash_password_fn("StudentDemo!2026"),
                "student",
                cohort,
                now,
            ),
            (
                "ciaran.byrne@nci-demo.example",
                "Ciaran Byrne",
                hash_password_fn("StudentDemo!2026"),
                "student",
                cohort,
                now,
            ),
            (
                "niamh.gallagher@nci-demo.example",
                "Niamh Gallagher",
                hash_password_fn("RepDemo!2026"),
                "rep",
                cohort,
                now,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO users (email, full_name, password_hash, role, cohort, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            demo_users,
        )

        user_ids = {
            row["email"]: row["id"]
            for row in conn.execute("SELECT id, email FROM users;").fetchall()
        }
        aoife_id = user_ids["aoife.brennan@nci-demo.example"]
        ciaran_id = user_ids["ciaran.byrne@nci-demo.example"]
        niamh_id = user_ids["niamh.gallagher@nci-demo.example"]

        demo_feedback = [
            (
                aoife_id,
                cohort,
                "Audio echo in Week 5 Cryptography recording",
                "Lectures",
                "The lecture capture for Tuesday's Cryptography session has a strong echo after the 35-minute mark, making key-exchange examples hard to follow.",
                "New",
                now,
                now,
            ),
            (
                aoife_id,
                cohort,
                "Draft timetable shows duplicate Tuesday lab slot",
                "Timetables",
                "The draft calendar lists two overlapping lab rooms for Tuesday afternoon; submitting this item as a separate New entry for deletion demo testing.",
                "New",
                now,
                now,
            ),
            (
                aoife_id,
                cohort,
                "Clarify IEEE referencing expectations for CA brief",
                "Assessments",
                "Several classmates are unsure whether RFC documents and OWASP cheat sheets should be cited with access dates in the IEEE reference list.",
                "In Review",
                now,
                now,
            ),
            (
                aoife_id,
                cohort,
                "Broken lab VM mirror link in Week 3 Moodle folder",
                "Learning Resources",
                "The secondary download mirror for the Week 3 vulnerable web app VM returns a 404 error when accessed off-campus.",
                "Resolved",
                now,
                now,
            ),
            (
                ciaran_id,
                cohort,
                "Room change notice needed for Thursday lab group",
                "Timetables",
                "Our Thursday practical room conflicted with another cohort this week; could the updated room allocation be posted before Monday?",
                "New",
                now,
                now,
            ),
            (
                ciaran_id,
                cohort,
                "Request walkthrough of DFD trust boundaries in tutorial",
                "Assessments",
                "It would help the class if next week's tutorial covered a quick example of marking trust boundaries on data flow diagrams.",
                "In Review",
                now,
                now,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO feedback (
                author_id, cohort, title, category, description, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            demo_feedback,
        )

        feedback_ids = {
            row["title"]: row["id"]
            for row in conn.execute("SELECT id, title FROM feedback;").fetchall()
        }

        demo_responses = [
            (
                feedback_ids["Clarify IEEE referencing expectations for CA brief"],
                niamh_id,
                "Thanks Aoife—I have raised this with the module lecturer and will post the confirmed IEEE citation guidance on the Group B announcement board once confirmed.",
                now,
            ),
            (
                feedback_ids["Broken lab VM mirror link in Week 3 Moodle folder"],
                niamh_id,
                "The lab technician updated the Moodle link to the working mirror this morning. Verified accessible off-campus.",
                now,
            ),
            (
                feedback_ids["Request walkthrough of DFD trust boundaries in tutorial"],
                niamh_id,
                "Good suggestion Ciaran—passed along to the tutor for next week's session agenda.",
                now,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO responses (feedback_id, rep_id, message, created_at)
            VALUES (?, ?, ?, ?);
            """,
            demo_responses,
        )
        conn.commit()
        return True
    finally:
        conn.close()


def init_db_and_seed(app: Flask, hash_password_fn: Any) -> None:
    """Ensure migrations and fictional demo seed data are applied for the app."""
    db_path = app.config["DATABASE_PATH"]
    run_migrations(db_path)
    seed_demo_data(db_path, hash_password_fn)


def reset_and_seed_db(database_path: str | Path, hash_password_fn: Any) -> list[str]:
    """Recreate a fresh local database from SQL migrations and insert fictional demo data."""
    db_path = Path(database_path)
    if db_path.exists():
        db_path.unlink()
    applied = run_migrations(db_path)
    seed_demo_data(db_path, hash_password_fn)
    return applied
