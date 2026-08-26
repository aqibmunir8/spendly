# Spec: Registration

## Overview

Turn the existing GET `/register` page into a working sign-up flow: accept POST, validate name/email/password, hash the password with werkzeug, insert a row into `users`, start a session, and redirect to `/profile`. This is the first auth step after database setup; login/logout come later, but registration must persist users and set `session['user_id']` so later steps can treat the visitor as logged in.

## Depends on

- Step 1 — Database setup (`01-database-setup.md`): `users` table, `get_db()`, parameterized inserts, werkzeug hashing already used in `seed_db()`.

## Routes

- `GET /register` — already implemented; keep rendering `register.html` (public). Pass `error=None` (or omit) so the existing `{% if error %}` block stays hidden.
- `POST /register` — same path; process the form, create the user, set session, redirect (public).
- No other new routes. Do not implement `/logout` or `/profile` beyond what already exists (profile remains a stub until Step 4). After successful register, redirect to `url_for('profile')` even though profile is still a stub.

## Database changes

No database changes. Use the existing `users` table (`id`, `name`, `email`, `password_hash`, `created_at`). Email uniqueness is already enforced.

Add a helper in `database/db.py` (not inline in the route), for example `create_user(name, email, password_hash)` and `get_user_by_email(email)`, using parameterized SQL only.

## Templates

- **Create:** none.
- **Modify:** `templates/register.html` — change `action="/register"` to `action="{{ url_for('register') }}"`. Optionally re-populate `name` and `email` on validation error. Keep the existing `error` flash/block.

## Files to change

- `app.py` — `SECRET_KEY`; `session`; `request`, `redirect`, `url_for`, `abort` as needed; `register()` handles GET and POST (`methods=['GET', 'POST']`).
- `database/db.py` — user lookup and insert helpers.
- `templates/register.html` — `url_for('register')` on the form action.

## Files to create

- None required. Optional: page-specific CSS only if auth styles are missing; prefer existing classes in `style.css`.

## New dependencies

No new dependencies. Use Flask session, `werkzeug.security.generate_password_hash`, and sqlite3 already in the project.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`); never store plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic only in `database/db.py`
- Never hardcode URLs in templates — `url_for()`
- `abort()` for HTTP errors, not raw error strings
- Do not implement stub routes for other steps (`/logout`, expenses CRUD)
- Set `app.secret_key` (env var preferred, with a dev fallback) so sessions work
- On duplicate email, re-render `register.html` with a clear `error` message (do not crash on UNIQUE constraint)
- Validate: name non-empty, email non-empty, password at least 8 characters (matches the placeholder)
- Successful POST: insert user, `session['user_id'] = new_id`, redirect to profile
- `PRAGMA foreign_keys = ON` remains in `get_db()`

## Definition of done

- [ ] `GET /register` still shows the create-account form
- [ ] Submitting valid name, email, and password (≥ 8 chars) inserts a `users` row with a hashed password (not plaintext)
- [ ] After success, the browser is redirected to `/profile` and `session` contains `user_id`
- [ ] Duplicate email re-renders the form with an error; no new row
- [ ] Password shorter than 8 characters re-renders with an error; no new row
- [ ] Empty name or email re-renders with an error
- [ ] Form action uses `url_for('register')`
- [ ] App still starts on port 5001 without errors
- [ ] Demo user `demo@spendly.com` is unchanged
