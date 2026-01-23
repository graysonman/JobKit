"""
FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

from .database import init_db, SessionLocal
from .models import MessageTemplate, UserProfile
from .routers import contacts, applications, companies, messages
from .routers import profile, resume
from .services.message_generator import get_default_templates


def seed_default_templates():
    """Seed default message templates if none exist."""
    db = SessionLocal()
    try:
        existing = db.query(MessageTemplate).first()
        if not existing:
            templates = get_default_templates()
            for t in templates:
                db_template = MessageTemplate(**t)
                db.add(db_template)
            db.commit()
            print(f"Seeded {len(templates)} default message templates")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    os.makedirs("data", exist_ok=True)
    init_db()
    seed_default_templates()
    yield


app = FastAPI(
    title="Job Search Toolkit",
    description="Personal networking and job application tracker",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])


# --- Page Routes ---

@app.get("/")
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/contacts")
async def contacts_page(request: Request):
    return templates.TemplateResponse("contacts.html", {"request": request})


@app.get("/applications")
async def applications_page(request: Request):
    return templates.TemplateResponse("applications.html", {"request": request})


@app.get("/companies")
async def companies_page(request: Request):
    return templates.TemplateResponse("companies.html", {"request": request})


@app.get("/messages")
async def messages_page(request: Request):
    return templates.TemplateResponse("messages.html", {"request": request})


@app.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/resume")
async def resume_page(request: Request):
    return templates.TemplateResponse("resume.html", {"request": request})
