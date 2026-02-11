# JobKit

A personal toolkit for managing your job search. Track applications, build your network, and get AI-powered help with cover letters, outreach messages, and resume tailoring — all in one place.

## What It Does

**Track Applications** — Follow every application from "saved" through "offer." See which companies have responded, what stage you're at, and what's next.

**Track Your Network** — Store contacts with their company, role, and LinkedIn. Know who to follow up with, who referred you, and when you last reached out.

**Help With Applications** — AI-powered tools analyze job descriptions, generate tailored cover letters, craft networking messages, and suggest resume improvements based on your actual experience.

## Features

### Application Tracker
- Pipeline tracking: saved → applied → phone screen → technical → onsite → offer
- Link applications to contacts for referral tracking
- Store job descriptions, salary info, and notes
- Dashboard with response rates and weekly activity

### Networking Contacts
- Store name, email, LinkedIn, company, role
- Categorize: recruiter, hiring manager, junior/senior dev
- Track alumni connections and relationship strength
- Follow-up date reminders
- Full message history per contact

### Company Research
- Track target companies with tech stack, culture notes, and interview process
- Priority ratings and Glassdoor scores
- Link companies to contacts and applications

### AI-Powered Tools
- **Cover Letter Generation** — Uses your resume and the job description to write tailored cover letters
- **Message Generation** — Personalized outreach for LinkedIn connection requests, InMails, follow-ups, thank-yous, and cold emails
- **Job Description Analysis** — Extracts required skills, experience level, red flags, and interview prep topics
- **Resume Tailoring** — Compares your resume against a job posting and suggests specific improvements
- **Skill Extraction** — Pulls skills from resumes or job descriptions with categorization

All AI features use Groq's cloud API (default: Llama 3.3 70B). If the AI is unavailable, everything falls back to template-based generation automatically.

### Resume Management
- Upload PDF or DOCX resumes
- Parsed and stored for AI context
- Edit skills, experience, and summary directly in the app

### Authentication
- Single-user mode for local use (no login required)
- Multi-user mode with email/password registration
- JWT access tokens with refresh token rotation
- Optional OAuth login (Google, GitHub)
- bcrypt password hashing
- Rate-limited login/register endpoints

## Quick Start

### Prerequisites
- Python 3.11+
- [Groq API key](https://console.groq.com/) (optional, for AI features)

### Installation

```bash
# Clone the repo
git clone https://github.com/graysonman/JobKit.git
cd JobKit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
```

### Set Up AI (Optional)

Add your Groq API key to `.env`:
```bash
JOBKIT_GROQ_API_KEY=your-api-key-here
```

Get a free API key at https://console.groq.com/. The app works without it — AI features will fall back to templates.

### Run

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000

### First Steps

1. Go to **Settings** and set up your profile (name, skills, elevator pitch)
2. Upload your **Resume** (PDF or DOCX) so the AI can reference your experience
3. Add **Companies** you're targeting
4. Add **Contacts** at those companies
5. Start tracking **Applications**
6. Use **Messages** to generate personalized outreach
7. Use the **Resume** tools to tailor your application for each role

## Configuration

All settings are in `.env` (see `.env.example` for documentation). Key options:

| Variable | Default | Description |
|----------|---------|-------------|
| `JOBKIT_SINGLE_USER_MODE` | `true` | Set `false` to require login |
| `JOBKIT_SECRET_KEY` | dev key | JWT signing key (change in production) |
| `JOBKIT_AI_ENABLED` | `true` | Toggle AI features |
| `JOBKIT_GROQ_API_KEY` | — | Groq API key (required for AI) |
| `JOBKIT_GROQ_MODEL` | `llama-3.3-70b-versatile` | Model to use |
| `JOBKIT_DATABASE_URL` | `sqlite:///./data/jobkit.db` | Database connection |

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, Alembic
- **Frontend**: Jinja2 templates, Tailwind CSS, vanilla JavaScript
- **Database**: SQLite (default) or PostgreSQL
- **AI**: Groq API (cloud LLM inference)
- **Auth**: python-jose (JWT), passlib (bcrypt), authlib (OAuth2)

## Project Structure

```
JobKit/
├── app/
│   ├── main.py                 # FastAPI app, routes, middleware
│   ├── config.py               # Environment-based configuration
│   ├── database.py             # Database setup and session management
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── auth/                   # Authentication system
│   │   ├── router.py           # Auth API endpoints
│   │   ├── service.py          # JWT, password hashing, token management
│   │   ├── models.py           # User, OAuth, RefreshToken models
│   │   ├── schemas.py          # Auth request/response schemas
│   │   ├── dependencies.py     # FastAPI auth dependencies
│   │   └── oauth.py            # Google/GitHub OAuth integration
│   ├── routers/                # API endpoint modules
│   │   ├── contacts.py
│   │   ├── applications.py
│   │   ├── companies.py
│   │   ├── messages.py
│   │   ├── profile.py
│   │   └── resume.py
│   ├── services/               # Business logic
│   │   ├── ai_service.py       # Groq API integration and AI generation
│   │   ├── ai_prompts.py       # Prompt templates (editable at runtime)
│   │   ├── message_generator.py
│   │   └── resume_helper.py
│   └── templates/              # Jinja2 HTML templates
├── static/
│   ├── css/styles.css
│   └── js/
│       ├── app.js              # Global utilities
│       └── auth.js             # Token management and fetch interceptor
├── scripts/
│   └── reset_password.py       # CLI password reset tool
├── alembic/                    # Database migrations
├── data/                       # SQLite database (gitignored)
├── .env.example                # Environment variable documentation
└── requirements.txt
```

## API Documentation

With the app running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Alt + 1-7` | Navigate between pages |
| `Alt + N` | Open "Add New" modal |
| `Escape` | Close any open modal |

## Password Reset

If you're running in multi-user mode and need to reset a password:

```bash
python scripts/reset_password.py user@email.com NewPassword123
```
