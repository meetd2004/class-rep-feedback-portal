"""Tests for secure file/image attachments, magic-byte validation, IDOR checks, and disk cleanup."""

from __future__ import annotations

import io
from pathlib import Path

from app.db import connect_sqlite
from tests.conftest import extract_csrf_token, login_as

# Minimal valid 1x1 PNG binary payload
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_student_can_attach_image_and_txt_visible_to_author_and_admin_only(app, client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))

    create_resp = client.post(
        "/feedback/new",
        content_type="multipart/form-data",
        data={
            "csrf_token": token,
            "title": "Screenshot of lab VM error",
            "category": "Learning Resources",
            "description": "Attached screenshot and log snippet from the Week 5 lab VM.",
            "attachments": [
                (io.BytesIO(VALID_PNG_BYTES), "../../evil_path/error_screen.png"),
                (io.BytesIO(b"Error code 404 on mirror"), "lab_log.txt"),
            ],
        },
        follow_redirects=True,
    )
    assert create_resp.status_code == 200
    detail_html = create_resp.get_data(as_text=True)
    assert "Attachments (2)" in detail_html
    assert "error_screen.png" in detail_html
    assert "lab_log.txt" in detail_html
    assert "../../" not in detail_html

    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        rows = conn.execute(
            "SELECT id, feedback_id, stored_filename, is_image FROM attachments ORDER BY id ASC;"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 2
    img_id, txt_id = rows[0]["id"], rows[1]["id"]
    fid = rows[0]["feedback_id"]
    assert rows[0]["is_image"] == 1
    assert rows[1]["is_image"] == 0
    assert (Path(app.config["UPLOAD_FOLDER"]) / rows[0]["stored_filename"]).is_file()

    # Author can download/view attachments
    img_resp = client.get(f"/attachments/{img_id}")
    assert img_resp.status_code == 200
    assert img_resp.data == VALID_PNG_BYTES
    assert img_resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert "inline" in img_resp.headers.get("Content-Disposition", "")

    txt_resp = client.get(f"/attachments/{txt_id}")
    assert txt_resp.status_code == 200
    assert "attachment" in txt_resp.headers.get("Content-Disposition", "")

    # Another student (Ciaran) gets 403 IDOR block on attachments
    client.post("/logout", data={"csrf_token": extract_csrf_token(detail_html)})
    login_as(client, "ciaran.byrne@nci-demo.example", "StudentDemo!2026")
    assert client.get(f"/attachments/{img_id}").status_code == 403
    assert client.get(f"/attachments/{txt_id}").status_code == 403

    # Out-of-cohort Group A rep gets 403
    ciaran_dash = client.get("/student/dashboard").get_data(as_text=True)
    client.post("/logout", data={"csrf_token": extract_csrf_token(ciaran_dash)})
    login_as(client, "groupa.rep@nci-demo.example", "RepDemo!2026")
    assert client.get(f"/attachments/{img_id}").status_code == 403

    # Group B Class Rep Admin sees attachments on queue & detail and can view them
    groupa_dash = client.get("/rep/dashboard").get_data(as_text=True)
    client.post("/logout", data={"csrf_token": extract_csrf_token(groupa_dash)})
    login_as(client, "niamh.gallagher@nci-demo.example", "RepDemo!2026")

    admin_queue = client.get("/rep/dashboard").get_data(as_text=True)
    assert "2 files" in admin_queue
    admin_detail = client.get(f"/rep/feedback/{fid}").get_data(as_text=True)
    assert "Attachments (2)" in admin_detail
    assert "error_screen.png" in admin_detail
    assert client.get(f"/attachments/{img_id}").status_code == 200
    assert client.get(f"/attachments/{txt_id}").status_code == 200


def test_attachment_validation_blocks_spoofed_magic_bytes_and_unsafe_extensions(client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))

    # Disallow SVG / HTML to prevent Stored XSS
    svg_resp = client.post(
        "/feedback/new",
        content_type="multipart/form-data",
        data={
            "csrf_token": token,
            "title": "Attempting SVG upload",
            "category": "Lectures",
            "description": "Trying to upload an active SVG file with embedded script.",
            "attachments": (io.BytesIO(b"<svg onload=alert(1)></svg>"), "xss.svg"),
        },
    )
    assert svg_resp.status_code == 200
    assert "Unsupported file type" in svg_resp.get_data(as_text=True)

    # Disallow HTML disguised with a .png extension (magic byte mismatch)
    spoof_resp = client.post(
        "/feedback/new",
        content_type="multipart/form-data",
        data={
            "csrf_token": token,
            "title": "Attempting spoofed PNG",
            "category": "Lectures",
            "description": "Trying to upload an HTML payload renamed to image.png.",
            "attachments": (io.BytesIO(b"<html><script>alert(1)</script></html>"), "fake.png"),
        },
    )
    assert spoof_resp.status_code == 200
    assert "failed signature validation" in spoof_resp.get_data(as_text=True)


def test_deleting_new_feedback_removes_attachment_files_from_disk(app, client) -> None:
    login_as(client, "aoife.brennan@nci-demo.example", "StudentDemo!2026")
    token = extract_csrf_token(client.get("/feedback/new").get_data(as_text=True))

    res = client.post(
        "/feedback/new",
        content_type="multipart/form-data",
        data={
            "csrf_token": token,
            "title": "Temporary upload to delete",
            "category": "Timetables",
            "description": "Uploading an attachment then deleting the New submission.",
            "attachments": (io.BytesIO(VALID_PNG_BYTES), "temp_pic.png"),
        },
        follow_redirects=True,
    )
    assert res.status_code == 200

    conn = connect_sqlite(app.config["DATABASE_PATH"])
    try:
        att = conn.execute(
            "SELECT id, feedback_id, stored_filename FROM attachments WHERE original_filename = 'temp_pic.png';"
        ).fetchone()
    finally:
        conn.close()
    assert att is not None
    stored_path = Path(app.config["UPLOAD_FOLDER"]) / att["stored_filename"]
    assert stored_path.is_file()

    del_token = extract_csrf_token(res.get_data(as_text=True))
    client.post(
        f"/feedback/{att['feedback_id']}/delete",
        data={"csrf_token": del_token},
        follow_redirects=True,
    )
    assert not stored_path.exists()
