"""
JobKit - FastAPI application entry point.

A personal job search toolkit for tracking applications, networking contacts,
and generating outreach messages.

# =============================================================================
# TODO: Multi-User Authentication (Feature 2)
# =============================================================================
# - Add auth router: from .auth import router as auth_router
# - Include router: app.include_router(auth_router, prefix="/auth", tags=["auth"])
# - Update CORS: specify actual origins in production
# - Protect page routes with authentication middleware
# - Add login/register pages to templates
# - Add JOBKIT_SINGLE_USER_MODE env check for backwards compatibility
# =============================================================================
"""
from fastapi import FastAPI, Request, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, date, timedelta
from typing import Optional, List
import logging
import os
import io
import csv
import json

from .database import init_db, SessionLocal, get_db
from .models import MessageTemplate, UserProfile, Contact, Application, Company, MessageHistory
from .routers import contacts, applications, companies, messages
from .routers import profile, resume
from .services.message_generator import get_default_templates
from .schemas import (
    SearchRequest, SearchResult, ContactResponse, CompanyResponse, ApplicationResponse,
    ExportRequest, ImportResult
)

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jobkit")


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
            logger.info(f"Seeded {len(templates)} default message templates")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    logger.info("Starting JobKit application...")
    os.makedirs("data", exist_ok=True)
    init_db()
    seed_default_templates()
    logger.info("JobKit ready!")
    yield
    logger.info("Shutting down JobKit...")


app = FastAPI(
    title="JobKit",
    description="Personal job search toolkit - track applications, manage networking contacts, and generate outreach messages",
    version="0.1.0",
    lifespan=lifespan
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# --- API Endpoints ---

@app.get("/api/health", tags=["system"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/stats", tags=["system"])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get summary statistics for dashboard."""
    # Contact stats
    total_contacts = db.query(func.count(Contact.id)).scalar() or 0
    contacts_needing_followup = db.query(func.count(Contact.id)).filter(
        Contact.next_follow_up <= date.today()
    ).scalar() or 0

    # Application stats
    total_applications = db.query(func.count(Application.id)).scalar() or 0
    active_applications = db.query(func.count(Application.id)).filter(
        Application.status.notin_(['rejected', 'withdrawn', 'ghosted', 'accepted'])
    ).scalar() or 0

    # Calculate response rate
    applied_count = db.query(func.count(Application.id)).filter(
        Application.status != 'saved'
    ).scalar() or 0
    got_response_count = db.query(func.count(Application.id)).filter(
        Application.status.in_(['phone_screen', 'technical', 'onsite', 'offer', 'accepted', 'rejected'])
    ).scalar() or 0
    response_rate = (got_response_count / applied_count * 100) if applied_count > 0 else 0

    # Company stats
    total_companies = db.query(func.count(Company.id)).scalar() or 0

    # Recent activity (last 7 days)
    week_ago = date.today() - timedelta(days=7)
    applications_this_week = db.query(func.count(Application.id)).filter(
        Application.created_at >= week_ago
    ).scalar() or 0
    contacts_this_week = db.query(func.count(Contact.id)).filter(
        Contact.created_at >= week_ago
    ).scalar() or 0

    return {
        "contacts": {
            "total": total_contacts,
            "needs_follow_up": contacts_needing_followup,
            "added_this_week": contacts_this_week
        },
        "applications": {
            "total": total_applications,
            "active": active_applications,
            "response_rate": round(response_rate, 1),
            "added_this_week": applications_this_week
        },
        "companies": {
            "total": total_companies
        }
    }


@app.post("/api/search", response_model=SearchResult, tags=["system"])
async def global_search(
    query: str = Query(..., min_length=1, max_length=200),
    search_in: Optional[str] = Query("contacts,companies,applications"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search across contacts, companies, and applications."""
    search_term = f"%{query}%"
    search_types = search_in.split(",") if search_in else ["contacts", "companies", "applications"]

    result = SearchResult()

    if "contacts" in search_types:
        contacts_query = db.query(Contact).filter(
            or_(
                Contact.name.ilike(search_term),
                Contact.company.ilike(search_term),
                Contact.email.ilike(search_term),
                Contact.notes.ilike(search_term)
            )
        ).limit(limit).all()
        result.contacts = [ContactResponse.model_validate(c) for c in contacts_query]

    if "companies" in search_types:
        companies_query = db.query(Company).filter(
            or_(
                Company.name.ilike(search_term),
                Company.industry.ilike(search_term),
                Company.tech_stack.ilike(search_term),
                Company.notes.ilike(search_term)
            )
        ).limit(limit).all()
        result.companies = [CompanyResponse.model_validate(c) for c in companies_query]

    if "applications" in search_types:
        applications_query = db.query(Application).filter(
            or_(
                Application.company_name.ilike(search_term),
                Application.role.ilike(search_term),
                Application.notes.ilike(search_term)
            )
        ).limit(limit).all()
        result.applications = [ApplicationResponse.model_validate(a) for a in applications_query]

    return result


@app.get("/api/export", tags=["system"])
async def export_data(
    format: str = Query("json", pattern="^(json|csv)$"),
    include_contacts: bool = True,
    include_applications: bool = True,
    include_companies: bool = True,
    include_messages: bool = False,
    db: Session = Depends(get_db)
):
    """Export all data as JSON or CSV."""
    data = {}

    if include_contacts:
        contacts = db.query(Contact).all()
        data["contacts"] = [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "linkedin_url": c.linkedin_url,
                "company": c.company,
                "role": c.role,
                "contact_type": c.contact_type,
                "is_alumni": c.is_alumni,
                "school_name": c.school_name,
                "connection_status": c.connection_status,
                "relationship_strength": c.relationship_strength,
                "last_contacted": str(c.last_contacted) if c.last_contacted else None,
                "next_follow_up": str(c.next_follow_up) if c.next_follow_up else None,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in contacts
        ]

    if include_applications:
        applications = db.query(Application).all()
        data["applications"] = [
            {
                "id": a.id,
                "company_name": a.company_name,
                "role": a.role,
                "job_url": a.job_url,
                "status": a.status,
                "applied_date": str(a.applied_date) if a.applied_date else None,
                "response_date": str(a.response_date) if a.response_date else None,
                "next_step": a.next_step,
                "next_step_date": str(a.next_step_date) if a.next_step_date else None,
                "salary_offered": a.salary_offered,
                "notes": a.notes,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in applications
        ]

    if include_companies:
        companies = db.query(Company).all()
        data["companies"] = [
            {
                "id": c.id,
                "name": c.name,
                "website": c.website,
                "linkedin_url": c.linkedin_url,
                "size": c.size,
                "industry": c.industry,
                "tech_stack": c.tech_stack,
                "culture_notes": c.culture_notes,
                "interview_process": c.interview_process,
                "glassdoor_rating": c.glassdoor_rating,
                "salary_range": c.salary_range,
                "priority": c.priority,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in companies
        ]

    if include_messages:
        messages = db.query(MessageHistory).all()
        data["messages"] = [
            {
                "id": m.id,
                "contact_id": m.contact_id,
                "message_type": m.message_type,
                "message_content": m.message_content,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "got_response": m.got_response
            }
            for m in messages
        ]

    if format == "json":
        return JSONResponse(
            content=data,
            headers={
                "Content-Disposition": f"attachment; filename=jobkit_export_{date.today()}.json"
            }
        )
    else:
        # CSV export - create a zip-like structure with multiple CSVs
        # For simplicity, we'll export as JSON for now
        # Full CSV export would require multiple files
        output = io.StringIO()

        # Export contacts as CSV
        if include_contacts and data.get("contacts"):
            writer = csv.DictWriter(output, fieldnames=data["contacts"][0].keys())
            writer.writeheader()
            writer.writerows(data["contacts"])

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=jobkit_contacts_{date.today()}.csv"
            }
        )


@app.post("/api/import", response_model=ImportResult, tags=["system"])
async def import_data(
    data: dict,
    db: Session = Depends(get_db)
):
    """Import data from JSON."""
    result = ImportResult()

    try:
        # Import contacts
        if "contacts" in data:
            for contact_data in data["contacts"]:
                # Remove id and timestamps for new records
                contact_data.pop("id", None)
                contact_data.pop("created_at", None)
                contact_data.pop("updated_at", None)

                # Check for duplicate by name and email
                existing = db.query(Contact).filter(
                    Contact.name == contact_data.get("name"),
                    Contact.email == contact_data.get("email")
                ).first()

                if not existing:
                    contact = Contact(**contact_data)
                    db.add(contact)
                    result.contacts_imported += 1

        # Import companies
        if "companies" in data:
            for company_data in data["companies"]:
                company_data.pop("id", None)
                company_data.pop("created_at", None)
                company_data.pop("updated_at", None)

                existing = db.query(Company).filter(
                    Company.name == company_data.get("name")
                ).first()

                if not existing:
                    company = Company(**company_data)
                    db.add(company)
                    result.companies_imported += 1

        # Import applications
        if "applications" in data:
            for app_data in data["applications"]:
                app_data.pop("id", None)
                app_data.pop("created_at", None)
                app_data.pop("updated_at", None)

                application = Application(**app_data)
                db.add(application)
                result.applications_imported += 1

        db.commit()

    except Exception as e:
        db.rollback()
        result.errors.append(str(e))
        logger.error(f"Import error: {e}")

    return result


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
