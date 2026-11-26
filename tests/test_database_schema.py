"""Tests verifying fresh SQLite schema migration, constraints, and repeatable demo seeding."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db import connect_sqlite, reset_and_seed_db, run_migrations, utc_now_iso
from app.security import hash_password


def test_fresh_database_migration_creates_tables_and_indexes(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh_schema.db"
    applied = run_migrations(db_path)
    assert applied == ["001_initial_schema.sql"]

    # Re-running migrations should be idempotent.
    assert run_migrations(db_path) == []

    conn = connect_sqlite(db_path)
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table';"
            ).fetchall()
        }
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index';"
            ).fetchall()
        }
    finally:
        conn.close()

    assert {"schema_migrations", "users", "feedback", "responses"}.issubset(tables)
    assert {
        "idx_feedback_author_id",
        "idx_feedback_cohort_status",
        "idx_responses_feedback_id",
    }.issubset(indexes)


def test_database_check_constraints_reject_invalid_role_category_and_status(tmp_path: Path) -> None:
    db_path = tmp_path / "constraints.db"
    run_migrations(db_path)
    now = utc_now_iso()

    conn = connect_sqlite(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO users (email, full_name, password_hash, role, cohort, created_at)
                VALUES ('bad@nci-demo.example', 'Bad Role', 'hash', 'admin', 'MSc Cybersecurity Group B', ?);
                """,
                (now,),
            )

        conn.execute(
            """
            INSERT INTO users (email, full_name, password_hash, role, cohort, created_at)
            VALUES ('valid@nci-demo.example', 'Valid Student', 'hash', 'student', 'MSc Cybersecurity Group B', ?);
            """,
            (now,),
        )
        uid = conn.execute("SELECT id FROM users WHERE email = 'valid@nci-demo.example';").fetchone()["id"]

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO feedback (author_id, cohort, title, category, description, status, created_at, updated_at)
                VALUES (?, 'MSc Cybersecurity Group B', 'Valid Title', 'UnknownCategory', 'Valid description text here.', 'New', ?, ?);
                """,
                (uid, now, now),
            )

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO feedback (author_id, cohort, title, category, description, status, created_at, updated_at)
                VALUES (?, 'MSc Cybersecurity Group B', 'Valid Title', 'Lectures', 'Valid description text here.', 'Archived', ?, ?);
                """,
                (uid, now, now),
            )
    finally:
        conn.close()


def test_reset_and_seed_db_produces_repeatable_fictional_dataset(tmp_path: Path) -> None:
    db_path = tmp_path / "repeatable_demo.db"
    applied_first = reset_and_seed_db(db_path, hash_password)
    assert applied_first == ["001_initial_schema.sql"]

    # Mutate database, then verify reset restores exact baseline counts.
    conn = connect_sqlite(db_path)
    try:
        conn.execute("DELETE FROM feedback;")
        conn.commit()
    finally:
        conn.close()

    applied_second = reset_and_seed_db(db_path, hash_password)
    assert applied_second == ["001_initial_schema.sql"]

    conn = connect_sqlite(db_path)
    try:
        user_count = conn.execute("SELECT COUNT(*) AS cnt FROM users;").fetchone()["cnt"]
        feedback_count = conn.execute("SELECT COUNT(*) AS cnt FROM feedback;").fetchone()["cnt"]
        response_count = conn.execute("SELECT COUNT(*) AS cnt FROM responses;").fetchone()["cnt"]
        aoife_new_count = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM feedback AS f
            JOIN users AS u ON u.id = f.author_id
            WHERE u.email = 'aoife.brennan@nci-demo.example' AND f.status = 'New';
            """
        ).fetchone()["cnt"]
    finally:
        conn.close()

    assert user_count == 3
    assert feedback_count == 6
    assert response_count == 3
    assert aoife_new_count == 2
