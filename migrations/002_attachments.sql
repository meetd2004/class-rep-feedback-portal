-- Migration 002: Secure file and image attachments linked to feedback submissions
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER NOT NULL,
    uploader_id INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    is_image INTEGER NOT NULL CHECK (is_image IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (feedback_id) REFERENCES feedback(id) ON DELETE CASCADE,
    FOREIGN KEY (uploader_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attachments_feedback_id ON attachments(feedback_id);
