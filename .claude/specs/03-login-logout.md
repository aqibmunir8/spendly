# Spec: Login and Logout

## Overview

Implement working authentication for the Spendly expense tracker. This step adds POST `/login` to verify credentials against the database, set `session['user_id']`, and redirect to `/profile`. It also implements `/logout` to clear the session and return the user to the landing page. This completes the core auth loop started in Step 2 (registration).

## Depends on

- Step 1 — Database setup (`01-database-setup.md`): `users` table, `get_db()`, `get_user_by_email()`, `PRAGMA foreign_keys = ON`, werkzeug hashing
- Step 2 — Registration (`02-registration.md`): `users` table populated, `session['user_id']` established on signup, `login.html` exists

## Routes

- `GET /login` — already implemented; keep rendering `login.html` (public)
- `POST /login` — same path; authenticate email/password, set session, redirect to `url_for('profile')` (public)
- `GET /logout` — clear session, redirect to `url_for('landing')` (logged-in only)

## Database changes

No database changes. Use the existing `users` table (`id`, `name`, `email`, `password_hash`, `created_at`).

Add a helper in `database/db.py` for password verification, e.g., `verify_password(password_hash, password)` using `werkzeug.security.check_password_hash`.

## Templates
 
- **Create:** none
- **Modify:** `templates/login.html` — change `action="/login"` to `action="{{ url_for('login') }}"`. Keep existing error block and form structure.

## Files to change

- `app.py` — `request`, `redirect`, `url_for`, `session`, `abort`; add `POST` to `/login` methods; implement `/logout` route; import `check_password_hash` from `werkzeug.security`
- `database/db.py` — add `verify_password(password_hash, password)` helper (or use `check_password_hash` directly in route, but prefer DB module for consistency)
- `templates/login.html` — form action uses `url_for('login')`

## Files to create

- None required

## New dependencies

No new dependencies. Use Flask session, `werkzeug.security.check_password_hash`, and sqlite3 already in the project.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash` on register, `check_password_hash` on login); never store plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic only in `database/db.py`
- Never hardcode URLs in templates — `url_for()`
- `abort()` for HTTP errors, not raw error strings
- Do not implement stub routes for other steps (`/profile`, expenses CRUD)
- On invalid credentials, re-render `login.html` with a clear `error` message (do not distinguish between "user not found" and "wrong password")
- Successful POST `/login`: `session['user_id'] = user.id`, redirect to profile
- `/logout`: `session.clear()`, redirect to landing
- `PRAGMA foreign_keys = ON` remains in `get_db()`

## Definition of done

- [ ] `GET /login` still shows the sign-in form
- [ ] Submitting valid email and password for an existing user sets `session['user_id']` and redirects to `/profile`
- [ ] Invalid email or wrong password re-renders the form with an error; no session is created
- [ ] Form action uses `url_for('login')`
- [ ] `GET /logout` clears the session and redirects to `/` (landing page)
- [ ] After logout, visiting `/profile` (stub) shows no user session
- [ ] Demo user `demo@spendly.com` / `demo123` can log in successfully
- [ ] App still starts on port 5001 without errors