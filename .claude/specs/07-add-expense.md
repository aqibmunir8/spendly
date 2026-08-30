# Spec: Add Expense

## Overview

This feature implements the ability for logged-in users to add new expenses to their Spendly account. Users can input the expense amount, select a category, set a date, and optionally add a description. The expense is then saved to the database and immediately visible on their profile page.

## Depends on

- Step 1: Database setup (expenses table must exist)
- Step 2: Registration (user accounts must exist)
- Step 3: Login + Logout (session must be set)
- Step 4: Profile Page (profile UI must be complete)
- Step 5: Backend Routes for Profile (query functions must exist)

## Routes

- GET /expenses/add — render the add expense form — logged-in only
- POST /expenses/add — process the form submission — logged-in only

## Database changes

No database changes. The existing `expenses` table with columns (id, user_id, amount, category, date, description, created_at) is sufficient.

## Templates

- **Create:** `templates/add-expense.html` — form page extending `base.html` with:
  - Amount input field (required, numeric)
  - Category select dropdown (required)
  - Date picker (required, defaults to today)
  - Description textarea (optional)
  - Submit button
  - Cancel link back to profile

- **Modify:** `templates/base.html` — add "Add Expense" link in navbar when logged in

## Files to change

- `app.py` — implement POST handler for `/expenses/add`:
  - Auth guard (redirect to /login if not authenticated)
  - Validate all required fields
  - Call new `create_expense()` function from `database/queries.py`
  - Redirect to `/profile` on success
  - Re-render form with error message on validation failure

- `database/queries.py` — add `create_expense()` function:
  - Insert new expense record into database
  - Return the new expense ID

- `templates/base.html` — add "Add Expense" link to navigation

## Files to create

- `templates/add-expense.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` for database operations
- Parameterised queries only — never string-format SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for all internal links
- Validation errors displayed inline on the form
- Amount must be a positive number
- Date cannot be in the future
- Categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other

## Definition of done

- [ ] Visiting GET /expenses/add without being logged in redirects to /login
- [ ] Visiting POST /expenses/add without being logged in redirects to /login
- [ ] Submitting valid form data creates a new expense in the database
- [ ] After successful submission, user is redirected to /profile
- [ ] Form displays validation errors for missing required fields
- [ ] Amount field only accepts positive numbers
- [ ] Date field defaults to today's date
- [ ] Category dropdown shows all 7 categories
- [ ] Description field is optional and accepts multiline text
- [ ] "Add Expense" link appears in navbar when user is logged in
- [ ] Cancel button returns user to /profile without saving
