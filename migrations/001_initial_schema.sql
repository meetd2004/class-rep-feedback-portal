-- Migration 001: Initial schema for Class Rep Feedback Portal (MSc Cybersecurity Group B)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'rep')),
    cohort TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL,
    cohort TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK (
        category IN ('Lectures', 'Assessments', 'Timetables', 'Learning Resources')
    ),
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'New' CHECK (
        status IN ('New', 'In Review', 'Resolved')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER NOT NULL,
    rep_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE,
    FOREIGN KEY (rep_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feedback_author_id ON feedback(author_id);
CREATE INDEX IF NOT EXISTS idx_feedback_cohort_status ON feedback(cohort, status);
CREATE INDEX IF NOT EXISTS idx_responses_feedback_id ON responses(feedback_id);
