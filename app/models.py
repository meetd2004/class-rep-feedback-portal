"""Domain models representing database entities, relationships, and row mappings."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class UserModel:
    """Application user scoped to a role ('student' or 'rep') and cohort."""

    id: int
    email: str
    full_name: str
    role: str
    cohort: str
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> UserModel:
        """Map a SQLite user row (excluding password_hash) into a domain record."""
        return cls(
            id=int(row["id"]),
            email=str(row["email"]),
            full_name=str(row["full_name"]),
            role=str(row["role"]),
            cohort=str(row["cohort"]),
            created_at=str(row["created_at"]),
        )


@dataclass(frozen=True)
class FeedbackModel:
    """Primary CRUD entity submitted by a student and reviewed by cohort class reps."""

    id: int
    author_id: int
    cohort: str
    title: str
    category: str
    description: str
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> FeedbackModel:
        """Map a SQLite feedback row into a domain record."""
        return cls(
            id=int(row["id"]),
            author_id=int(row["author_id"]),
            cohort=str(row["cohort"]),
            title=str(row["title"]),
            category=str(row["category"]),
            description=str(row["description"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )


@dataclass(frozen=True)
class ResponseModel:
    """Official class representative reply linked to a parent Feedback record."""

    id: int
    feedback_id: int
    rep_id: int
    message: str
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ResponseModel:
        """Map a SQLite response row into a domain record."""
        return cls(
            id=int(row["id"]),
            feedback_id=int(row["feedback_id"]),
            rep_id=int(row["rep_id"]),
            message=str(row["message"]),
            created_at=str(row["created_at"]),
        )
