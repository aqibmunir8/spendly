# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spendly is a personal expense tracking web application built with Flask. This is a teaching/learning project where students implement features incrementally. Many routes and database functions are stubbed out as placeholders for future implementation.

## Development Commands

**Start the development server:**
```bash
python app.py
```
The app runs on http://localhost:5001 with debug mode enabled.

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run tests:**
```bash
pytest
```

**Run specific test:**
```bash
pytest path/to/test_file.py::test_function_name
```

## Architecture

### Backend Structure
- **app.py**: Main Flask application with all route definitions. Routes are organized into two sections:
  - Implemented routes: landing page, auth pages (login/register), legal pages (terms/privacy)
  - Placeholder routes: logout, profile, expense CRUD operations (marked with "coming in Step X" messages)
- **database/db.py**: Database layer (currently a stub with instructions for implementation)
  - Should contain: `get_db()`, `init_db()`, `seed_db()`
  - Uses SQLite with row_factory and foreign keys enabled

### Frontend Structure
- **templates/**: Jinja2 HTML templates
  - `base.html`: Base template with common layout
  - `landing.html`: Marketing landing page with hero section and YouTube modal
  - `login.html`, `register.html`: Authentication pages
  - `terms.html`, `privacy.html`: Legal pages
- **static/css/**: Stylesheets (including `landing.css` for landing page-specific styles)
- **static/js/**: JavaScript files (vanilla JS only, no frameworks)
- **static/reference/**: Design mockups and reference images

### Key Implementation Notes
- No JavaScript frameworks are used — all frontend interactivity uses vanilla JS
- The landing page includes a modal for YouTube video embeds that stops video playback on close
- Database implementation is pending — expect `get_db()` to return SQLite connections with proper configuration
- Authentication and expense management features are scaffolded but not yet implemented

## Git Workflow

Commit messages follow the pattern: `<area>: <description>`
- Example: `landing: add youtube modal on see how it works click`
- Common areas: `landing`, `database`, `auth`, `expenses`
