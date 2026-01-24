# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is JobKit?

JobKit is a local job search management web application for software developers. It helps track networking contacts, job applications, company research, message templates, and resume information.

## Development Commands

```bash
# Run development server (with hot reload)
python -m uvicorn app.main:app --reload

# Run production server
python -m uvicorn app.main:app

# Install dependencies
pip install -r requirements.txt
```

The app runs at http://localhost:8000. API docs available at /docs (Swagger) and /redoc.

## Architecture

```
FastAPI (app/main.py)
    ├── Page Routes → Jinja2 templates (app/templates/)
    ├── API Routes (app/routers/)
    │   └── /api/{contacts,applications,companies,messages,profile,resume}
    └── Services (app/services/)
         ├── message_generator.py - Template-based message generation
         └── resume_helper.py - Resume parsing utilities
    ↓
SQLAlchemy ORM (app/models.py)
    ↓
SQLite (data/job_search.db, auto-created on startup)
```

**Frontend stack:** Jinja2 templates + Tailwind CSS (CDN) + HTMX 1.9.10 + vanilla JavaScript

**Backend stack:** FastAPI + SQLAlchemy 2.0 + Pydantic 2.0 + SQLite

## Key Files

- `app/main.py` - Entry point, page routes, lifespan handler (db init, template seeding)
- `app/models.py` - 8 SQLAlchemy models: Contact, Company, Application, MessageTemplate, MessageHistory, UserProfile, Interaction
- `app/schemas.py` - Pydantic schemas with custom validators for URLs/emails
- `app/database.py` - Database connection, session management
- `static/css/styles.css` - Custom styles beyond Tailwind
- `static/js/app.js` - API utilities, modals, toast notifications, keyboard shortcuts

## API Patterns

- All API endpoints return JSON, prefixed with `/api/`
- Use `Depends(get_db)` for database sessions
- Standard CRUD pattern: GET (list/detail), POST (create), PUT (update), DELETE
- Global endpoints: `/api/health`, `/api/stats`, `/api/search`, `/api/export`, `/api/import`

## Frontend Patterns

- HTMX for partial updates without full page reload
- Modal system with click-outside and Escape key close
- Toast notifications via `showToast(message, type)`
- API calls via `api(url, method, body)` helper
- Keyboard shortcuts: Alt+1-6 for navigation, Alt+N for new item modal

## Database

- SQLite at `data/job_search.db` (configurable via `DATABASE_URL` env var)
- Auto-initialized on startup via `init_db()`
- Default message templates seeded if none exist
- UserProfile constrained to single row (id=1)

## Message Generator Service

Located in `app/services/message_generator.py`:
- Template placeholders: `{name}`, `{company}`, `{my_title}`, `{role}`, etc.
- Platform character limits enforced (LinkedIn connection: 300, InMail: 1900)
- Overused phrase detection with improvement suggestions (80+ phrases)

## Application Status Pipeline

For job applications: `saved` → `applied` → `phone_screen` → `technical` → `onsite` → `offer` → `accepted`/`rejected`/`withdrawn`/`ghosted`

## Planned Features (from TODOs)

- Phase 5: OpenAI integration, NLTK/spaCy for resume NLP
- Phase 6: Database backup, Alembic migrations
- Frontend: Dark mode, mobile improvements, accessibility
