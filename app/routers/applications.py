"""
CRUD API for job applications.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from ..database import get_db
from ..models import Application
from ..schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse

router = APIRouter()

# Application status pipeline order
STATUS_ORDER = ['saved', 'applied', 'phone_screen', 'technical', 'onsite', 'offer', 'accepted', 'rejected', 'withdrawn', 'ghosted']

@router.get("/", response_model=List[ApplicationResponse])
def list_applications(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    company_name: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """List applications with optional filters."""
    query = db.query(Application)

    if status:
        query = query.filter(Application.status == status)
    if company_name:
        query = query.filter(Application.company_name.ilike(f"%{company_name}%"))
    if active_only:
        query = query.filter(Application.status.notin_(['rejected', 'withdrawn', 'ghosted', 'accepted']))

    # TODO Phase 6: Add sorting by applied_date, status, company
    # TODO Phase 6: Add date range filter

    return query.offset(skip).limit(limit).all()


@router.get("/stats")
def get_application_stats(db: Session = Depends(get_db)):
    """Get application statistics for dashboard."""
    from sqlalchemy import func

    total = db.query(func.count(Application.id)).scalar()

    status_counts = {}
    for status in STATUS_ORDER:
        count = db.query(func.count(Application.id)).filter(Application.status == status).scalar()
        status_counts[status] = count

    active_count = db.query(func.count(Application.id)).filter(
        Application.status.notin_(['rejected', 'withdrawn', 'ghosted', 'accepted'])
    ).scalar()

    # Response rate: applications that got past 'applied' status
    applied_or_further = db.query(func.count(Application.id)).filter(
        Application.status != 'saved'
    ).scalar()

    got_response = db.query(func.count(Application.id)).filter(
        Application.status.in_(['phone_screen', 'technical', 'onsite', 'offer', 'accepted', 'rejected'])
    ).scalar()

    response_rate = (got_response / applied_or_further * 100) if applied_or_further > 0 else 0

    return {
        "total": total,
        "active": active_count,
        "by_status": status_counts,
        "response_rate": round(response_rate, 1)
    }


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: int, db: Session = Depends(get_db)):
    """Get a specific application."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/", response_model=ApplicationResponse)
def create_application(application: ApplicationCreate, db: Session = Depends(get_db)):
    """Create a new application."""
    db_application = Application(**application.model_dump())
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(application_id: int, application: ApplicationUpdate, db: Session = Depends(get_db)):
    """Update an application."""
    db_application = db.query(Application).filter(Application.id == application_id).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")

    update_data = application.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_application, key, value)

    db.commit()
    db.refresh(db_application)
    return db_application


@router.delete("/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    """Delete an application."""
    db_application = db.query(Application).filter(Application.id == application_id).first()
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(db_application)
    db.commit()
    return {"message": "Application deleted"}


# TODO Phase 5: Add endpoint to analyze job description and suggest resume tweaks
# TODO Phase 6: Add timeline endpoint showing application history
