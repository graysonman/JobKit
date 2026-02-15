"""
JobKit - CRUD API for company research.

Endpoints for managing target companies, including research notes,
tech stack, culture, and interview process information.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional

from ..database import get_db
from ..models import Company, Contact, Application
from ..schemas import (
    CompanyCreate, CompanyUpdate, CompanyResponse,
    CompanyStats, ContactResponse, ApplicationResponse
)
from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..query_helpers import user_query, get_owned_or_404
from ..rate_limit import limiter, RATE_LIMIT_GENERAL

router = APIRouter()


@router.get("/", response_model=List[CompanyResponse])
def list_companies(
    skip: int = 0,
    limit: int = 100,
    size: Optional[str] = None,
    industry: Optional[str] = None,
    min_priority: Optional[int] = None,
    search: Optional[str] = None,
    tech: Optional[str] = None,
    sort_by: Optional[str] = Query(None, pattern="^(name|priority|glassdoor_rating|created_at|size)$"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List companies with optional filters, search, and sorting."""
    query = user_query(db, Company, current_user)

    # Filters
    if size:
        query = query.filter(Company.size == size)
    if industry:
        query = query.filter(Company.industry.ilike(f"%{industry}%"))
    if min_priority is not None:
        query = query.filter(Company.priority >= min_priority)

    # Tech stack filter
    if tech:
        query = query.filter(Company.tech_stack.ilike(f"%{tech}%"))

    # Search across multiple fields
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Company.name.ilike(search_term),
                Company.industry.ilike(search_term),
                Company.tech_stack.ilike(search_term),
                Company.notes.ilike(search_term),
                Company.culture_notes.ilike(search_term)
            )
        )

    # Sorting
    if sort_by:
        sort_column = getattr(Company, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(Company.priority.desc(), Company.name.asc())

    return query.offset(skip).limit(limit).all()


@router.get("/stats", response_model=CompanyStats)
def get_company_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get company statistics."""
    base = user_query(db, Company, current_user)
    total = base.count()

    # Count by size
    by_size = {}
    size_counts = base.with_entities(
        Company.size, func.count(Company.id)
    ).group_by(Company.size).all()
    for size, count in size_counts:
        by_size[size or "unspecified"] = count

    # Count by priority
    by_priority = {}
    priority_counts = base.with_entities(
        Company.priority, func.count(Company.id)
    ).group_by(Company.priority).all()
    for priority, count in priority_counts:
        by_priority[str(priority)] = count

    # Companies with applications
    app_base = user_query(db, Application, current_user)
    with_applications = app_base.filter(
        Application.company_id.isnot(None)
    ).with_entities(func.count(func.distinct(Application.company_id))).scalar() or 0

    return CompanyStats(
        total=total,
        by_size=by_size,
        by_priority=by_priority,
        with_applications=with_applications
    )


@router.get("/by-tech", response_model=List[CompanyResponse])
def get_companies_by_tech(
    tech: str = Query(..., min_length=1, description="Technology to search for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Find companies using a specific technology."""
    companies = user_query(db, Company, current_user).filter(
        Company.tech_stack.ilike(f"%{tech}%")
    ).order_by(Company.priority.desc()).all()
    return companies


@router.get("/top-priority", response_model=List[CompanyResponse])
def get_top_priority_companies(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get highest priority companies."""
    companies = user_query(db, Company, current_user).filter(
        Company.priority >= 3
    ).order_by(Company.priority.desc(), Company.name.asc()).limit(limit).all()
    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific company."""
    return get_owned_or_404(db, Company, company_id, current_user, "Company")


@router.get("/{company_id}/applications", response_model=List[ApplicationResponse])
def get_company_applications(
    company_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all applications at a specific company."""
    get_owned_or_404(db, Company, company_id, current_user, "Company")

    applications = user_query(db, Application, current_user).filter(
        Application.company_id == company_id
    ).order_by(Application.created_at.desc()).limit(limit).all()
    return applications


@router.get("/{company_id}/contacts", response_model=List[ContactResponse])
def get_company_contacts(
    company_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all contacts at a specific company."""
    company = get_owned_or_404(db, Company, company_id, current_user, "Company")

    contacts = user_query(db, Contact, current_user).filter(
        Contact.company.ilike(f"%{company.name}%")
    ).order_by(Contact.created_at.desc()).limit(limit).all()
    return contacts


@router.get("/{company_id}/summary")
def get_company_summary(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a summary of all data related to a company."""
    company = get_owned_or_404(db, Company, company_id, current_user, "Company")

    app_base = user_query(db, Application, current_user)

    # Count applications
    application_count = app_base.filter(
        Application.company_id == company_id
    ).count()

    # Count contacts
    contact_count = user_query(db, Contact, current_user).filter(
        Contact.company.ilike(f"%{company.name}%")
    ).count()

    # Get application status breakdown
    status_counts = app_base.filter(
        Application.company_id == company_id
    ).with_entities(
        Application.status, func.count(Application.id)
    ).group_by(Application.status).all()

    return {
        "company": CompanyResponse.model_validate(company),
        "applications": {
            "total": application_count,
            "by_status": {status: count for status, count in status_counts}
        },
        "contacts": {
            "total": contact_count
        }
    }


@router.post("/", response_model=CompanyResponse)
@limiter.limit(RATE_LIMIT_GENERAL)
def create_company(
    request: Request,
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new company."""
    # Check for duplicate name within user's companies
    existing = user_query(db, Company, current_user).filter(
        Company.name == company.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company with this name already exists")

    db_company = Company(**company.model_dump(), user_id=current_user.id)
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.patch("/{company_id}", response_model=CompanyResponse)
@limiter.limit(RATE_LIMIT_GENERAL)
def update_company(
    request: Request,
    company_id: int,
    company: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a company."""
    db_company = get_owned_or_404(db, Company, company_id, current_user, "Company")

    update_data = company.model_dump(exclude_unset=True)

    # Check for duplicate name if updating name
    if 'name' in update_data and update_data['name'] != db_company.name:
        existing = user_query(db, Company, current_user).filter(
            Company.name == update_data['name']
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Company with this name already exists")

    for key, value in update_data.items():
        setattr(db_company, key, value)

    db.commit()
    db.refresh(db_company)
    return db_company


@router.patch("/{company_id}/priority")
def update_company_priority(
    company_id: int,
    priority: int = Query(..., ge=0, le=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a company's priority."""
    db_company = get_owned_or_404(db, Company, company_id, current_user, "Company")
    db_company.priority = priority
    db.commit()
    db.refresh(db_company)
    return {"message": f"Priority updated to {priority}", "company_id": company_id}


@router.delete("/{company_id}")
@limiter.limit(RATE_LIMIT_GENERAL)
def delete_company(
    request: Request,
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a company."""
    db_company = get_owned_or_404(db, Company, company_id, current_user, "Company")
    db.delete(db_company)
    db.commit()
    return {"message": "Company deleted"}


# --- Bulk operations ---

@router.post("/bulk", response_model=List[CompanyResponse])
@limiter.limit(RATE_LIMIT_GENERAL)
def bulk_create_companies(
    request: Request,
    companies: List[CompanyCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create multiple companies at once."""
    created_companies = []
    for company_data in companies:
        # Skip duplicates within user's companies
        existing = user_query(db, Company, current_user).filter(
            Company.name == company_data.name
        ).first()
        if not existing:
            db_company = Company(**company_data.model_dump(), user_id=current_user.id)
            db.add(db_company)
            created_companies.append(db_company)

    db.commit()
    for company in created_companies:
        db.refresh(company)

    return created_companies
