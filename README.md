# Job Search & Networking Toolkit

A Python-based local web application to help with job searching in software development. Combines networking contact management with job application tracking and preparation tools.

## Features

### Networking Contact Tracker
- Store contacts with name, LinkedIn URL, company, role
- Track alumni status and connection status
- Categorize contacts: recruiter, junior dev, senior dev, hiring manager
- Generate personalized outreach messages from templates
- Track follow-up dates and message history

### Application Tracker
- Track job applications through the pipeline
- Status tracking: saved, applied, phone screen, technical, onsite, offer, etc.
- Link applications to contacts (referrals)
- Store job descriptions for reference

### Company Research
- Store notes about target companies
- Track company size, tech stack, culture notes
- Priority rating system
- Link to related job postings and contacts

### Resume & Cover Letter Helper
- Analyze job descriptions to extract key requirements
- Check resume match against job descriptions
- Generate cover letters based on your profile
- Get suggestions for resume improvements

### Message Generator
- Pre-built templates for connection requests, InMails, follow-ups
- Personalization based on contact and your profile
- Message history tracking

## Quick Start

### Installation

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
python -m uvicorn app.main:app --reload
```

Access the app at: http://localhost:8000

### First Steps

1. Go to **Settings** and set up your profile (name, skills, elevator pitch)
2. Add some **Contacts** you want to reach out to
3. Add **Companies** you're interested in
4. Track your **Applications**
5. Use **Messages** to generate personalized outreach
6. Use **Resume** helper to tailor your applications

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite
- **Frontend**: HTML, Tailwind CSS (CDN), HTMX, JavaScript
- **Database**: SQLite (local file in `data/job_search.db`)

## Project Structure

```
networking-bot/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # SQLite setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/             # API endpoints
│   │   ├── contacts.py
│   │   ├── applications.py
│   │   ├── companies.py
│   │   ├── messages.py
│   │   ├── profile.py
│   │   └── resume.py
│   ├── services/            # Business logic
│   │   ├── message_generator.py
│   │   └── resume_helper.py
│   └── templates/           # HTML templates
├── static/
│   ├── css/styles.css
│   └── js/app.js
├── data/                    # SQLite database (gitignored)
├── docs/
│   └── schema.sql          # Database schema reference
├── requirements.txt
└── README.md
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Keyboard Shortcuts

- `Alt + 1-7`: Quick navigation between pages
- `Alt + N`: Open "Add New" modal (context-dependent)
- `Escape`: Close any open modal

## Data Export

Go to Settings to export your data as JSON files.

## Tips for Job Searching

1. **Prioritize warm connections**: Alumni and 2nd-degree connections convert better
2. **Quality over quantity**: 5 personalized messages beat 50 generic ones
3. **Follow up**: Many opportunities come from polite follow-ups after 1-2 weeks
4. **Target companies, not just jobs**: Research 10-20 companies you'd love to work for
5. **Junior devs are great contacts**: They recently went through the process and can refer you
