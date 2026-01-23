"""
JobKit - CRUD API for company research.

Endpoints for managing target companies, including research notes,
tech stack, culture, and interview process information.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional

from ..database import get_db
from ..models import Company, Contact, Application
from ..schemas import (
    CompanyCreate, CompanyUpdate, CompanyResponse,
    CompanyStats, ContactResponse, ApplicationResponse
)

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
    db: Session = Depends(get_db)
):
    """List companies with optional filters, search, and sorting."""
    query = db.query(Company)

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
def get_company_stats(db: Session = Depends(get_db)):
    """Get company statistics."""
    total = db.query(func.count(Company.id)).scalar() or 0

    # Count by size
    by_size = {}
    size_counts = db.query(Company.size, func.count(Company.id)).group_by(Company.size).all()
    for size, count in size_counts:
        by_size[size or "unspecified"] = count

    # Count by priority
    by_priority = {}
    priority_counts = db.query(Company.priority, func.count(Company.id)).group_by(Company.priority).all()
    for priority, count in priority_counts:
        by_priority[str(priority)] = count

    # Companies with applications
    with_applications = db.query(func.count(func.distinct(Application.company_id))).filter(
        Application.company_id.isnot(None)
    ).scalar() or 0

    return CompanyStats(
        total=total,
        by_size=by_size,
        by_priority=by_priority,
        with_applications=with_applications
    )


@router.get("/by-tech", response_model=List[CompanyResponse])
def get_companies_by_tech(
    tech: str = Query(..., min_length=1, description="Technology to search for"),
    db: Session = Depends(get_db)
):
    """Find companies using a specific technology."""
    companies = db.query(Company).filter(
        Company.tech_stack.ilike(f"%{tech}%")
    ).order_by(Company.priority.desc()).all()
    return companies


@router.get("/top-priority", response_model=List[CompanyResponse])
def get_top_priority_companies(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get highest priority companies."""
    companies = db.query(Company).filter(
        Company.priority >= 3
    ).order_by(Company.priority.desc(), Company.name.asc()).limit(limit).all()
    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """Get a specific company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("/{company_id}/applications", response_model=List[ApplicationResponse])
def get_company_applications(
    company_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all applications at a specific company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    applications = db.query(Application).filter(
        Application.company_id == company_id
    ).order_by(Application.created_at.desc()).limit(limit).all()
    return applications


@router.get("/{company_id}/contacts", response_model=List[ContactResponse])
def get_company_contacts(
    company_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all contacts at a specific company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Find contacts whose company name matches
    contacts = db.query(Contact).filter(
        Contact.company.ilike(f"%{company.name}%")
    ).order_by(Contact.created_at.desc()).limit(limit).all()
    return contacts


@router.get("/{company_id}/summary")
def get_company_summary(company_id: int, db: Session = Depends(get_db)):
    """Get a summary of all data related to a company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Count applications
    application_count = db.query(func.count(Application.id)).filter(
        Application.company_id == company_id
    ).scalar() or 0

    # Count contacts
    contact_count = db.query(func.count(Contact.id)).filter(
        Contact.company.ilike(f"%{company.name}%")
    ).scalar() or 0

    # Get application status breakdown
    status_counts = db.query(Application.status, func.count(Application.id)).filter(
        Application.company_id == company_id
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
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company."""
    # Check for duplicate name
    existing = db.query(Company).filter(Company.name == company.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company with this name already exists")

    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(company_id: int, company: CompanyUpdate, db: Session = Depends(get_db)):
    """Update a company."""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company.model_dump(exclude_unset=True)

    # Check for duplicate name if updating name
    if 'name' in update_data and update_data['name'] != db_company.name:
        existing = db.query(Company).filter(Company.name == update_data['name']).first()
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
    db: Session = Depends(get_db)
):
    """Update a company's priority."""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db_company.priority = priority
    db.commit()
    db.refresh(db_company)
    return {"message": f"Priority updated to {priority}", "company_id": company_id}


@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    """Delete a company."""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(db_company)
    db.commit()
    return {"message": "Company deleted"}


# --- Bulk operations ---

@router.post("/bulk", response_model=List[CompanyResponse])
def bulk_create_companies(
    companies: List[CompanyCreate],
    db: Session = Depends(get_db)
):
    """Create multiple companies at once."""
    created_companies = []
    for company_data in companies:
        # Skip duplicates
        existing = db.query(Company).filter(Company.name == company_data.name).first()
        if not existing:
            db_company = Company(**company_data.model_dump())
            db.add(db_company)
            created_companies.append(db_company)

    db.commit()
    for company in created_companies:
        db.refresh(company)

    return created_companies
