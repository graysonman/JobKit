"""
JobKit - CRUD API for job applications.

Endpoints for tracking job applications through the hiring pipeline,
from initial save through offer/rejection.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import date, timedelta

from ..database import get_db
from ..models import Application, Company
from ..schemas import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    ApplicationStats
)
from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..query_helpers import user_query, get_owned_or_404
from ..rate_limit import limiter, RATE_LIMIT_GENERAL

router = APIRouter()

# Application status pipeline order
STATUS_ORDER = ['saved', 'applied', 'phone_screen', 'technical', 'onsite', 'offer', 'accepted', 'rejected', 'withdrawn', 'ghosted']
ACTIVE_STATUSES = ['saved', 'applied', 'phone_screen', 'technical', 'onsite', 'offer']
TERMINAL_STATUSES = ['accepted', 'rejected', 'withdrawn', 'ghosted']


@router.get("/", response_model=List[ApplicationResponse])
def list_applications(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    company_name: Optional[str] = None,
    active_only: bool = False,
    search: Optional[str] = None,
    applied_after: Optional[date] = None,
    applied_before: Optional[date] = None,
    sort_by: Optional[str] = Query(None, pattern="^(company_name|role|applied_date|status|created_at|next_step_date)$"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List applications with optional filters, search, and sorting."""
    query = user_query(db, Application, current_user)

    # Filters
    if status:
        query = query.filter(Application.status == status)
    if company_name:
        query = query.filter(Application.company_name.ilike(f"%{company_name}%"))
    if active_only:
        query = query.filter(Application.status.in_(ACTIVE_STATUSES))

    # Date range filters
    if applied_after:
        query = query.filter(Application.applied_date >= applied_after)
    if applied_before:
        query = query.filter(Application.applied_date <= applied_before)

    # Search across multiple fields
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Application.company_name.ilike(search_term),
                Application.role.ilike(search_term),
                Application.notes.ilike(search_term),
                Application.next_step.ilike(search_term)
            )
        )

    # Sorting
    if sort_by:
        sort_column = getattr(Application, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(Application.created_at.desc())

    return query.offset(skip).limit(limit).all()


@router.get("/stats", response_model=ApplicationStats)
def get_application_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get application statistics for dashboard."""
    base = user_query(db, Application, current_user)
    total = base.count()

    # Count by status
    by_status = {}
    status_counts = base.with_entities(
        Application.status, func.count(Application.id)
    ).group_by(Application.status).all()
    for status, count in status_counts:
        by_status[status] = count

    # Active applications
    active = base.filter(Application.status.in_(ACTIVE_STATUSES)).count()

    # Response rate
    applied_count = base.filter(Application.status != 'saved').count()
    got_response = base.filter(
        Application.status.in_(['phone_screen', 'technical', 'onsite', 'offer', 'accepted', 'rejected'])
    ).count()
    response_rate = (got_response / applied_count * 100) if applied_count > 0 else 0

    # Average days to response
    apps_with_response = base.filter(
        Application.applied_date.isnot(None),
        Application.response_date.isnot(None)
    ).all()

    avg_days = None
    if apps_with_response:
        total_days = sum(
            (app.response_date - app.applied_date).days
            for app in apps_with_response
        )
        avg_days = total_days / len(apps_with_response)

    # This week's applications
    week_ago = date.today() - timedelta(days=7)
    applications_this_week = base.filter(Application.created_at >= week_ago).count()

    # This month's applications
    month_ago = date.today() - timedelta(days=30)
    applications_this_month = base.filter(Application.created_at >= month_ago).count()

    return ApplicationStats(
        total=total,
        active=active,
        by_status=by_status,
        response_rate=round(response_rate, 1),
        avg_days_to_response=round(avg_days, 1) if avg_days else None,
        applications_this_week=applications_this_week,
        applications_this_month=applications_this_month
    )


@router.get("/stale", response_model=List[ApplicationResponse])
def get_stale_applications(
    days: int = Query(14, ge=7, le=60, description="Days without activity to consider stale"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Find applications that may have been ghosted (no activity for N days)."""
    cutoff_date = date.today() - timedelta(days=days)

    stale_apps = user_query(db, Application, current_user).filter(
        Application.status.in_(['applied', 'phone_screen', 'technical', 'onsite']),
        Application.updated_at < cutoff_date
    ).order_by(Application.updated_at.asc()).all()

    return stale_apps


@router.get("/upcoming", response_model=List[ApplicationResponse])
def get_upcoming_steps(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get applications with next steps scheduled in the next N days."""
    future_date = date.today() + timedelta(days=days)
    applications = user_query(db, Application, current_user).filter(
        Application.next_step_date.isnot(None),
        Application.next_step_date <= future_date,
        Application.next_step_date >= date.today()
    ).order_by(Application.next_step_date.asc()).all()
    return applications


@router.get("/funnel")
def get_application_funnel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get conversion funnel metrics for applications."""
    base = user_query(db, Application, current_user)

    saved = base.filter(Application.status == 'saved').count()
    applied = base.filter(Application.status != 'saved').count()
    phone_screen = base.filter(
        Application.status.in_(['phone_screen', 'technical', 'onsite', 'offer', 'accepted'])
    ).count()
    technical = base.filter(
        Application.status.in_(['technical', 'onsite', 'offer', 'accepted'])
    ).count()
    onsite = base.filter(
        Application.status.in_(['onsite', 'offer', 'accepted'])
    ).count()
    offer = base.filter(
        Application.status.in_(['offer', 'accepted'])
    ).count()
    accepted = base.filter(Application.status == 'accepted').count()

    def rate(num, denom):
        return round(num / denom * 100, 1) if denom > 0 else 0

    return {
        "funnel": {
            "saved": saved,
            "applied": applied,
            "phone_screen": phone_screen,
            "technical": technical,
            "onsite": onsite,
            "offer": offer,
            "accepted": accepted
        },
        "conversion_rates": {
            "applied_to_phone_screen": rate(phone_screen, applied),
            "phone_screen_to_technical": rate(technical, phone_screen),
            "technical_to_onsite": rate(onsite, technical),
            "onsite_to_offer": rate(offer, onsite),
            "offer_to_accepted": rate(accepted, offer),
            "applied_to_offer": rate(offer, applied)
        }
    }


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific application."""
    return get_owned_or_404(db, Application, application_id, current_user, "Application")


@router.post("/", response_model=ApplicationResponse)
@limiter.limit(RATE_LIMIT_GENERAL)
def create_application(
    request: Request,
    application: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new application."""
    db_application = Application(**application.model_dump(), user_id=current_user.id)
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application


@router.patch("/{application_id}", response_model=ApplicationResponse)
@limiter.limit(RATE_LIMIT_GENERAL)
def update_application(
    request: Request,
    application_id: int,
    application: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an application."""
    db_application = get_owned_or_404(db, Application, application_id, current_user, "Application")

    update_data = application.model_dump(exclude_unset=True)

    # Auto-set response_date when status changes from applied to something else
    if 'status' in update_data:
        new_status = update_data['status']
        old_status = db_application.status
        if old_status == 'applied' and new_status in ['phone_screen', 'technical', 'onsite', 'offer', 'rejected']:
            if not db_application.response_date:
                db_application.response_date = date.today()

    for key, value in update_data.items():
        setattr(db_application, key, value)

    db.commit()
    db.refresh(db_application)
    return db_application


@router.delete("/{application_id}")
@limiter.limit(RATE_LIMIT_GENERAL)
def delete_application(
    request: Request,
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an application."""
    db_application = get_owned_or_404(db, Application, application_id, current_user, "Application")
    db.delete(db_application)
    db.commit()
    return {"message": "Application deleted"}


@router.patch("/{application_id}/mark-ghosted")
def mark_as_ghosted(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark an application as ghosted."""
    db_application = get_owned_or_404(db, Application, application_id, current_user, "Application")
    db_application.status = "ghosted"
    db.commit()
    db.refresh(db_application)
    return {"message": "Application marked as ghosted", "application_id": application_id}


@router.patch("/{application_id}/advance")
def advance_application(
    application_id: int,
    next_step: Optional[str] = None,
    next_step_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Advance an application to the next pipeline stage."""
    db_application = get_owned_or_404(db, Application, application_id, current_user, "Application")

    current_status = db_application.status
    if current_status in TERMINAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Cannot advance application in {current_status} status")

    # Find next status in pipeline
    try:
        current_index = STATUS_ORDER.index(current_status)
        next_index = current_index + 1
        while next_index < len(STATUS_ORDER) and STATUS_ORDER[next_index] in TERMINAL_STATUSES:
            next_index += 1
        if next_index >= len(STATUS_ORDER) or STATUS_ORDER[next_index] in TERMINAL_STATUSES:
            raise HTTPException(status_code=400, detail="No more stages to advance to")
        new_status = STATUS_ORDER[next_index]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid current status")

    # Set response date if advancing from applied
    if current_status == 'applied' and not db_application.response_date:
        db_application.response_date = date.today()

    db_application.status = new_status
    if next_step:
        db_application.next_step = next_step
    if next_step_date:
        db_application.next_step_date = next_step_date

    db.commit()
    db.refresh(db_application)

    return {
        "message": f"Application advanced to {new_status}",
        "previous_status": current_status,
        "new_status": new_status
    }


# --- Bulk operations ---

@router.post("/bulk", response_model=List[ApplicationResponse])
@limiter.limit(RATE_LIMIT_GENERAL)
def bulk_create_applications(
    request: Request,
    applications: List[ApplicationCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create multiple applications at once."""
    created_apps = []
    for app_data in applications:
        db_app = Application(**app_data.model_dump(), user_id=current_user.id)
        db.add(db_app)
        created_apps.append(db_app)

    db.commit()
    for app in created_apps:
        db.refresh(app)

    return created_apps
