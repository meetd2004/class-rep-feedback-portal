# Class Rep Feedback Portal (MSc Cybersecurity Group B)

## 1. Project Title and Overview

**Class Rep Feedback Portal** is a role-based, security-focused web application built for **National College of Ireland — MSc Cybersecurity Group B**. It enables students to submit private, structured feedback on lectures, assessments, timetables, and learning resources, while allowing assigned Group B class representatives to review submissions, post official responses, and track status progression from `New` to `In Review` to `Resolved`.

The application is designed around secure web development principles across all layers (database, backend, templates, and HTTP transport configuration), enforcing authentication, server-side authorization, CSRF protection, output escaping, and parameterised queries.

### Stack Decision
This repository uses **Python 3.12, Flask 3.1.3, SQLite, Jinja2 templates, plain CSS, Flask-WTF (`CSRFProtect`), and `argon2-cffi`** because the existing codebase and commit history (`b7ec7c2`–`0f3f4f9`) already established and verified this stack with automated `pytest` and `Bandit` checks.

### Role Matrix and First-Version Scope

| Capability / Route Scope | Unauthenticated | Student (`Group B`) | Class Rep (`Group B`) |
| :--- | :--- | :--- | :--- |
| Sign in / Sign out | Allowed (`POST /login` only) | Allowed (`POST /logout` + CSRF) | Allowed (`POST /logout` + CSRF) |
| Create feedback (`New`) | Denied (redirect to login) | Allowed | Denied (`403`) |
| View submission list & detail | Denied (redirect to login) | Own submissions only (`403` on others) | All `Group B` submissions (`403` on other cohorts) |
| Edit / Delete submission | Denied | Own submissions while status is `New` (`403` once `In Review`/`Resolved`) | Denied (`403`) |
| Change status (`New` → `In Review` → `Resolved`) | Denied | Denied (`403`) | Allowed (`Group B` only) |
| Post official reply | Denied | Denied (`403`) | Allowed (`Group B` only; moves `New` → `In Review`) |

**Scope Boundaries (v1):**
- Scoped to a single cohort (**MSc Cybersecurity Group B**) with two fictional student accounts and one fictional class rep account.
- **Feedback** is the primary entity demonstrating all four CRUD operations (`Create`, `Read`, `Update`, `Delete`), with deletion confirmed before execution.
- Public self-registration, anonymous feedback submissions, and a separate admin dashboard are intentionally outside the first version.

---

## 2. Features and Security Objectives

### Functional Features
- **Role-Based Authentication:** Sign-in and CSRF-protected sign-out redirecting students and class reps to their dedicated dashboards.
- **Student Feedback CRUD (Create, Read, Update, Delete):**
  - **Create:** Submit categorised feedback (`Lectures`, `Assessments`, `Timetables`, `Learning Resources`) initialized server-side to `New`.
  - **Read:** View personal submission summary counts, submission list, full details, and class rep responses.
  - **Update:** Edit title, category, or description while status remains `New`.
  - **Delete:** Permanently delete a submission (with confirmation prompt) while status remains `New`, with foreign-key `ON DELETE CASCADE` cleanup.
- **Class Rep Review Workflow:**
  - View all submissions scoped strictly to **MSc Cybersecurity Group B**.
  - Filter the queue by category and status (`New`, `In Review`, `Resolved`).
  - Post official responses (automatically promoting `New` submissions to `In Review`) and advance status to `Resolved`.
- **Resilient UI States:** Empty states for dashboards/filters, per-field server validation feedback, and safe custom error pages (`400`, `403`, `404`, `500`).

### Security Objectives (SR1–SR5)
1. **SR1 — Authentication & Password Hashing:** Passwords hashed with **Argon2id** (`argon2-cffi`); generic authentication error messages and uniform verification timing prevent user enumeration.
2. **SR2 — Session & CSRF Protection:** Server-signed cookies configured with `HttpOnly`, `SameSite=Lax`, 1-hour lifetime, and configurable `Secure` flag; session regenerated on login; **Flask-WTF `CSRFProtect`** enforced on all state-changing `POST` routes.
3. **SR3 — Role, Cohort & Ownership Access Control:** Server-side decorators (`@login_required`, `@role_required`) and `get_authorized_feedback()` enforce cohort (`MSc Cybersecurity Group B`), role (`student`/`rep`), authorship, and status (`New`-only edits/deletes) before every read or mutation—preventing IDOR and horizontal/vertical privilege escalation.
4. **SR4 — Server-Side Validation & Safe Rendering:** Strict server-side length checks and category/status allow-lists; Jinja2 auto-escaping combined with `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, and a strict `Content-Security-Policy` (zero inline scripts or styles).
5. **SR5 — Parameterised Database Access:** Static SQLite queries using `?` parameter bindings with `PRAGMA foreign_keys = ON` and database `CHECK` constraints, eliminating SQL injection vectors.

---

## 3. Project Structure

```text
Class_Rep_Feedback/
├── .env.example                  # Sample environment variables (never commit real .env)
├── .gitignore                    # Excludes .venv, instance/*.db, .env, caches
├── requirements.txt              # Pinned dependency bounds (Flask, Flask-WTF, argon2-cffi, pytest, bandit)
├── run.py                        # Local entry point (binds 127.0.0.1:5000, debug=False)
├── migrations/
│   └── 001_initial_schema.sql    # Users, Feedback, Responses tables, indexes, FK & CHECK constraints
├── app/
│   ├── __init__.py               # Flask app factory, CSRFProtect, security headers, error handlers
│   ├── config.py                 # Environment configuration and domain allow-lists / transitions
│   ├── db.py                     # Parameterised SQLite connection helper, migration runner, fictional seeds
│   ├── security.py               # Argon2id hashing, RBAC/ownership guards, server-side validators
│   ├── routes/
│   │   ├── __init__.py           # Blueprint registration
│   │   ├── auth.py               # /, /login, /logout
│   │   ├── student.py            # /student/dashboard, /feedback/new, /feedback/<id>, /edit, /delete
│   │   └── rep.py                # /rep/dashboard, /rep/feedback/<id>/respond, /status
│   ├── templates/
│   │   ├── base.html             # Shared layout, navigation, flash stack, CSRF logout
│   │   ├── login.html            # Clean sign-in form
│   │   ├── student_dashboard.html
│   │   ├── feedback_form.html    # Create and edit feedback form with validation feedback
│   │   ├── feedback_detail.html  # Detail view, status progression, rep response form, responses list
│   │   ├── rep_dashboard.html    # Rep review queue with category & status filters
│   │   └── error.html            # Custom non-leaking HTTP error page
│   └── static/
│       ├── css/styles.css        # Responsive, accessible stylesheet
│       └── js/app.js             # CSP-compliant delete confirm and character counter
└── tests/
    ├── conftest.py               # Isolated temp SQLite fixtures & CSRF helpers
    ├── test_auth_and_csrf.py     # Hashing, role redirects, session flags, headers, CSRF rejection
    ├── test_student_crud.py      # CRUD lifecycle, validation, status locks, cascade deletion
    ├── test_access_control.py    # Auth redirects, IDOR checks, RBAC, cohort isolation
    └── test_rep_workflow.py      # Queue filters, responses, status workflow, XSS & SQLi tests
```

---

## 4. Setup and Installation Instructions

### Prerequisites
- Python **3.12+**

### Local Setup (Windows PowerShell)
1. **Clone or open the repository directory:**
   ```powershell
   cd c:\Class_Rep_Feedback
   ```
2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
4. **Configure environment variables (optional for local demo):**
   Copy `.env.example` to `.env` and set a strong random `SECRET_KEY`. When omitted in local development, the app generates a runtime secret key automatically.
5. **Run the application:**
   ```powershell
   python run.py
   ```
   On first startup, the app automatically applies `migrations/001_initial_schema.sql` to `instance/feedback_portal.db` and seeds the fictional Group B demo accounts and feedback items.
6. Open `http://127.0.0.1:5000` in your browser.

*(To re-initialize or verify migrations manually via Flask CLI: `flask --app run init-db`.)*

---

## 5. Usage Guidelines

All seeded accounts and submissions are **100% fictional** for demonstration and testing:

| Name | Email | Password | Role | Cohort |
| :--- | :--- | :--- | :--- | :--- |
| Aoife Brennan | `aoife.brennan@nci-demo.example` | `StudentDemo!2026` | Student | MSc Cybersecurity Group B |
| Ciaran Byrne | `ciaran.byrne@nci-demo.example` | `StudentDemo!2026` | Student | MSc Cybersecurity Group B |
| Niamh Gallagher | `niamh.gallagher@nci-demo.example` | `RepDemo!2026` | Class Rep | MSc Cybersecurity Group B |

### Recommended Walkthrough
1. **Sign in as Aoife (Student):** View only Aoife's submissions, create a new feedback item (status `New`), edit it, and test deleting a `New` item.
2. **Verify Privacy (Cross-Student Isolation):** Sign in as Ciaran and confirm Aoife's submissions do not appear—and attempting to visit Aoife's feedback URL directly returns **HTTP 403 Access Denied**.
3. **Sign in as Niamh (Class Rep):** Filter the Group B queue by category/status, open a `New` item, post an official response (status moves to `In Review`), and advance status to `Resolved`.
4. **Verify Status Lock:** Sign back in as Aoife to see the class rep's response and confirm Edit/Delete controls are locked once status is `In Review` or `Resolved`.

---

## 6. Security Improvements

- **Argon2id Credential Storage:** Replaced weak or legacy hashes with memory-hard Argon2id (`time_cost=2, memory_cost=65536`) plus dummy hash verification on unknown emails.
- **Session Hardening & CSRF:** Session cleared on login/logout to prevent session fixation; `HttpOnly`, `SameSite=Lax`, and CSRF tokens enforced on all state-changing actions including `POST /logout`.
- **Centralised Server-Side Authorization:** Every read, update, delete, status transition, and response action invokes `get_authorized_feedback()` to verify cohort, role, ownership, and `New` status before touching data.
- **XSS & Clickjacking Defence:** Automatic Jinja2 HTML escaping paired with `Content-Security-Policy` (no `'unsafe-inline'`), `X-Frame-Options: DENY`, and `X-Content-Type-Options: nosniff`.
- **SQL Injection Prevention:** Exclusively static parameterised SQLite queries (`?` placeholders) and database-level `CHECK` / `FOREIGN KEY ... ON DELETE CASCADE` constraints.

---

## 7. Testing Process

### Functional & Security Test Suite (`pytest`)
Run the automated test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
- **Latest Verified Result:** **19 passed** across 4 test modules covering authentication, Argon2id hashing, CSRF rejection (`400`), CRUD & cascade deletion, status locks (`403`), horizontal IDOR (`403`), vertical RBAC (`403`), cohort isolation (`403`), XSS HTML escaping, and SQL injection payloads.

### Static Application Security Testing (`Bandit`)
Run SAST across application source code:
```powershell
.\.venv\Scripts\bandit.exe -r app run.py
```
- **Latest Verified Result:** **892 lines scanned, 0 issues identified** (0 Low, 0 Medium, 0 High, 0 `#nosec` suppressions).

---

## 8. Contributions and References

### Frameworks & Libraries
- **Flask** (`Flask`) — Web framework & Jinja2 templating
- **Flask-WTF** (`CSRFProtect`) — Cross-Site Request Forgery protection
- **argon2-cffi** (`PasswordHasher`) — Argon2id password hashing
- **pytest** — Automated functional and security verification
- **Bandit** — Python Static Application Security Testing (SAST)
- **SQLite** — Embedded relational database engine

### Security References
- OWASP Foundation, *OWASP Top Ten Web Application Security Risks*, 2021.
- OWASP Foundation, *OWASP Cheat Sheet Series (Authentication, Cross-Site Request Forgery Prevention, SQL Injection Prevention, Cross Site Scripting Prevention)*.
- National Institute of Standards and Technology (NIST), *Digital Identity Guidelines (SP 800-63B)*.
