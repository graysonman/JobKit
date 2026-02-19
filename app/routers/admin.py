"""
JobKit - Admin API Endpoints

Platform-wide metrics, user management, diagnostics, and audit log.
All endpoints require admin privileges via get_current_admin_user dependency.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from typing import Optional
from datetime import datetime, date, timedelta
import json

from ..database import get_db
from ..models import Contact, Application, Company, MessageHistory, UserProfile
from ..auth.dependencies import get_current_admin_user, log_admin_action, get_client_ip
from ..auth.models import User, AdminAuditLog, RefreshToken
from ..rate_limit import limiter, RATE_LIMIT_ADMIN

router = APIRouter()


# =============================================================================
# 2.1 — System Metrics
# =============================================================================

@router.get("/metrics/overview")
@limiter.limit(RATE_LIMIT_ADMIN)
def metrics_overview(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Platform-wide overview: user counts and total records per table."""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_ago = today_start - timedelta(days=7)
    month_ago = today_start - timedelta(days=30)

    # User counts
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(User.is_verified == True).scalar() or 0
    admin_users = db.query(func.count(User.id)).filter(User.is_admin == True).scalar() or 0

    # Signups
    signups_today = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar() or 0
    signups_week = db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar() or 0
    signups_month = db.query(func.count(User.id)).filter(User.created_at >= month_ago).scalar() or 0

    # Record totals
    total_contacts = db.query(func.count(Contact.id)).scalar() or 0
    total_applications = db.query(func.count(Application.id)).scalar() or 0
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    total_messages = db.query(func.count(MessageHistory.id)).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
            "admin": admin_users,
        },
        "signups": {
            "today": signups_today,
            "week": signups_week,
            "month": signups_month,
        },
        "records": {
            "contacts": total_contacts,
            "applications": total_applications,
            "companies": total_companies,
            "messages": total_messages,
        },
    }


@router.get("/metrics/growth")
@limiter.limit(RATE_LIMIT_ADMIN)
def metrics_growth(
    request: Request,
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Daily signup counts for charting over 7d, 30d, or 90d."""
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    start = datetime.utcnow() - timedelta(days=days)

    # Get daily signup counts using date truncation
    rows = (
        db.query(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count"),
        )
        .filter(User.created_at >= start)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
        .all()
    )

    # Build a complete date series (fill gaps with 0)
    daily = {}
    for i in range(days):
        d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        daily[d] = 0
    for row in rows:
        day_str = str(row.day)
        if day_str in daily:
            daily[day_str] = row.count

    return {
        "period": period,
        "data": [{"date": k, "signups": v} for k, v in daily.items()],
    }


@router.get("/metrics/engagement")
@limiter.limit(RATE_LIMIT_ADMIN)
def metrics_engagement(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Active users, average records per user, feature adoption rates."""
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = db.query(func.count(User.id)).scalar() or 1  # avoid div/0

    # Active users by recent record creation (any table)
    def active_since(since):
        """Count distinct users who created any record since the given time."""
        contact_users = db.query(Contact.user_id).filter(Contact.created_at >= since)
        app_users = db.query(Application.user_id).filter(Application.created_at >= since)
        company_users = db.query(Company.user_id).filter(Company.created_at >= since)
        msg_users = db.query(MessageHistory.user_id).filter(MessageHistory.sent_at >= since)
        all_active = contact_users.union(app_users).union(company_users).union(msg_users).subquery()
        return db.query(func.count()).select_from(all_active).scalar() or 0

    active_day = active_since(day_ago)
    active_week = active_since(week_ago)
    active_month = active_since(month_ago)

    # Average records per user
    avg_contacts = (db.query(func.count(Contact.id)).scalar() or 0) / total_users
    avg_applications = (db.query(func.count(Application.id)).scalar() or 0) / total_users
    avg_companies = (db.query(func.count(Company.id)).scalar() or 0) / total_users
    avg_messages = (db.query(func.count(MessageHistory.id)).scalar() or 0) / total_users

    # Feature adoption: users with >0 records in each table
    users_with_contacts = db.query(func.count(func.distinct(Contact.user_id))).scalar() or 0
    users_with_apps = db.query(func.count(func.distinct(Application.user_id))).scalar() or 0
    users_with_companies = db.query(func.count(func.distinct(Company.user_id))).scalar() or 0
    users_with_messages = db.query(func.count(func.distinct(MessageHistory.user_id))).scalar() or 0

    # Profile / resume completion
    users_with_profile = db.query(func.count(UserProfile.id)).scalar() or 0
    users_with_resume = (
        db.query(func.count(UserProfile.id))
        .filter(UserProfile.resume_data.isnot(None))
        .scalar()
        or 0
    )

    return {
        "active_users": {
            "day": active_day,
            "week": active_week,
            "month": active_month,
        },
        "avg_per_user": {
            "contacts": round(avg_contacts, 1),
            "applications": round(avg_applications, 1),
            "companies": round(avg_companies, 1),
            "messages": round(avg_messages, 1),
        },
        "feature_adoption": {
            "contacts": {"users": users_with_contacts, "pct": round(users_with_contacts / total_users * 100, 1)},
            "applications": {"users": users_with_apps, "pct": round(users_with_apps / total_users * 100, 1)},
            "companies": {"users": users_with_companies, "pct": round(users_with_companies / total_users * 100, 1)},
            "messages": {"users": users_with_messages, "pct": round(users_with_messages / total_users * 100, 1)},
            "profile": {"users": users_with_profile, "pct": round(users_with_profile / total_users * 100, 1)},
            "resume": {"users": users_with_resume, "pct": round(users_with_resume / total_users * 100, 1)},
        },
    }


@router.get("/metrics/applications")
@limiter.limit(RATE_LIMIT_ADMIN)
def metrics_applications(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Platform-wide application funnel, avg response time, source stats, offer rate."""
    # Status distribution
    status_rows = (
        db.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    status_distribution = {status: count for status, count in status_rows}
    total_apps = sum(status_distribution.values()) or 1

    # Average response time (applied_date → response_date) for apps that have both
    avg_response = (
        db.query(
            func.avg(func.julianday(Application.response_date) - func.julianday(Application.applied_date))
        )
        .filter(
            Application.applied_date.isnot(None),
            Application.response_date.isnot(None),
        )
        .scalar()
    )

    # Source effectiveness
    source_rows = (
        db.query(Application.source, func.count(Application.id))
        .filter(Application.source.isnot(None))
        .group_by(Application.source)
        .all()
    )
    source_stats = {source: count for source, count in source_rows}

    # Offer rate
    offer_count = status_distribution.get("offer", 0) + status_distribution.get("accepted", 0)
    applied_count = sum(v for k, v in status_distribution.items() if k != "saved")

    return {
        "status_distribution": status_distribution,
        "total_applications": total_apps,
        "avg_response_days": round(avg_response, 1) if avg_response else None,
        "source_stats": source_stats,
        "offer_rate": round(offer_count / applied_count * 100, 1) if applied_count else 0,
    }


# =============================================================================
# 2.2 — User Management
# =============================================================================

@router.get("/users")
@limiter.limit(RATE_LIMIT_ADMIN)
def list_users(
    request: Request,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    is_admin_filter: Optional[bool] = Query(None, alias="is_admin"),
    sort_by: str = Query("created_at", pattern="^(name|email|created_at|is_active)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Paginated user list with search, filters, sorting, and per-user record counts."""
    query = db.query(User)

    # Search
    if search:
        term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(term)) | (User.email.ilike(term))
        )

    # Filters
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    if is_admin_filter is not None:
        query = query.filter(User.is_admin == is_admin_filter)

    # Total count (before pagination)
    total = query.count()

    # Sort
    sort_col = getattr(User, sort_by, User.created_at)
    query = query.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

    # Paginate
    users = query.offset((page - 1) * per_page).limit(per_page).all()

    # Per-user record counts (batch query)
    user_ids = [u.id for u in users]

    contact_counts = dict(
        db.query(Contact.user_id, func.count(Contact.id))
        .filter(Contact.user_id.in_(user_ids))
        .group_by(Contact.user_id)
        .all()
    ) if user_ids else {}

    app_counts = dict(
        db.query(Application.user_id, func.count(Application.id))
        .filter(Application.user_id.in_(user_ids))
        .group_by(Application.user_id)
        .all()
    ) if user_ids else {}

    company_counts = dict(
        db.query(Company.user_id, func.count(Company.id))
        .filter(Company.user_id.in_(user_ids))
        .group_by(Company.user_id)
        .all()
    ) if user_ids else {}

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
                "records": {
                    "contacts": contact_counts.get(u.id, 0),
                    "applications": app_counts.get(u.id, 0),
                    "companies": company_counts.get(u.id, 0),
                },
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/users/{user_id}")
@limiter.limit(RATE_LIMIT_ADMIN)
def get_user_detail(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Detailed view of a single user: account info, all stats, recent activity."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Record counts
    contacts = db.query(func.count(Contact.id)).filter(Contact.user_id == user_id).scalar() or 0
    applications = db.query(func.count(Application.id)).filter(Application.user_id == user_id).scalar() or 0
    companies = db.query(func.count(Company.id)).filter(Company.user_id == user_id).scalar() or 0
    messages = db.query(func.count(MessageHistory.id)).filter(MessageHistory.user_id == user_id).scalar() or 0

    # Profile status
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    has_profile = profile is not None
    has_resume = profile is not None and profile.resume_data is not None

    # Application status breakdown
    status_rows = (
        db.query(Application.status, func.count(Application.id))
        .filter(Application.user_id == user_id)
        .group_by(Application.status)
        .all()
    )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "records": {
            "contacts": contacts,
            "applications": applications,
            "companies": companies,
            "messages": messages,
        },
        "application_statuses": {s: c for s, c in status_rows},
        "has_profile": has_profile,
        "has_resume": has_resume,
    }


@router.patch("/users/{user_id}/activate")
@limiter.limit(RATE_LIMIT_ADMIN)
def activate_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Set a user's is_active to True."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    db.commit()

    log_admin_action(db, admin, "activate_user", target_user_id=user_id, ip_address=get_client_ip(request))
    return {"message": f"User {user.email} activated", "is_active": True}


@router.patch("/users/{user_id}/deactivate")
@limiter.limit(RATE_LIMIT_ADMIN)
def deactivate_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Set a user's is_active to False and revoke all their refresh tokens."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False

    # Revoke all refresh tokens for this user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked == False,
    ).update({"revoked": True})

    db.commit()

    log_admin_action(db, admin, "deactivate_user", target_user_id=user_id, ip_address=get_client_ip(request))
    return {"message": f"User {user.email} deactivated", "is_active": False}


@router.patch("/users/{user_id}/promote")
@limiter.limit(RATE_LIMIT_ADMIN)
def promote_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Grant admin privileges to a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = True
    db.commit()

    log_admin_action(db, admin, "promote_user", target_user_id=user_id, ip_address=get_client_ip(request))
    return {"message": f"User {user.email} promoted to admin", "is_admin": True}


@router.patch("/users/{user_id}/demote")
@limiter.limit(RATE_LIMIT_ADMIN)
def demote_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Remove admin privileges from a user."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot demote yourself")

    admin_count = db.query(User).filter(User.is_admin == True).count()
    if admin_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot demote the last admin")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = False
    db.commit()

    log_admin_action(db, admin, "demote_user", target_user_id=user_id, ip_address=get_client_ip(request))
    return {"message": f"User {user.email} demoted from admin", "is_admin": False}


@router.patch("/users/{user_id}/verify")
@limiter.limit(RATE_LIMIT_ADMIN)
def verify_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Force-verify a user's email."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()

    log_admin_action(db, admin, "verify_user", target_user_id=user_id, ip_address=get_client_ip(request))
    return {"message": f"User {user.email} email verified", "is_verified": True}


# =============================================================================
# 2.3 — User Data Browsing (support/diagnostics)
# =============================================================================

@router.get("/users/{user_id}/contacts")
@limiter.limit(RATE_LIMIT_ADMIN)
def browse_user_contacts(
    request: Request,
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Paginated contacts for a specific user (audit logged)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(Contact).filter(Contact.user_id == user_id)
    total = query.count()
    contacts = query.order_by(Contact.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    log_admin_action(
        db, admin, "view_user_data",
        target_user_id=user_id,
        details={"data_type": "contacts", "page": page},
        ip_address=get_client_ip(request),
    )

    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "company": c.company,
                "role": c.role,
                "contact_type": c.contact_type,
                "connection_status": c.connection_status,
                "last_contacted": str(c.last_contacted) if c.last_contacted else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contacts
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/users/{user_id}/applications")
@limiter.limit(RATE_LIMIT_ADMIN)
def browse_user_applications(
    request: Request,
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Paginated applications for a specific user (audit logged)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(Application).filter(Application.user_id == user_id)
    total = query.count()
    apps = query.order_by(Application.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    log_admin_action(
        db, admin, "view_user_data",
        target_user_id=user_id,
        details={"data_type": "applications", "page": page},
        ip_address=get_client_ip(request),
    )

    return {
        "items": [
            {
                "id": a.id,
                "company_name": a.company_name,
                "role": a.role,
                "status": a.status,
                "applied_date": str(a.applied_date) if a.applied_date else None,
                "response_date": str(a.response_date) if a.response_date else None,
                "source": a.source,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in apps
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/users/{user_id}/companies")
@limiter.limit(RATE_LIMIT_ADMIN)
def browse_user_companies(
    request: Request,
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Paginated companies for a specific user (audit logged)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(Company).filter(Company.user_id == user_id)
    total = query.count()
    companies = query.order_by(Company.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    log_admin_action(
        db, admin, "view_user_data",
        target_user_id=user_id,
        details={"data_type": "companies", "page": page},
        ip_address=get_client_ip(request),
    )

    return {
        "items": [
            {
                "id": c.id,
                "name": c.name,
                "website": c.website,
                "industry": c.industry,
                "size": c.size,
                "priority": c.priority,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in companies
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/users/{user_id}/messages")
@limiter.limit(RATE_LIMIT_ADMIN)
def browse_user_messages(
    request: Request,
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Paginated message history for a specific user (audit logged)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(MessageHistory).filter(MessageHistory.user_id == user_id)
    total = query.count()
    messages = query.order_by(MessageHistory.sent_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    log_admin_action(
        db, admin, "view_user_data",
        target_user_id=user_id,
        details={"data_type": "messages", "page": page},
        ip_address=get_client_ip(request),
    )

    return {
        "items": [
            {
                "id": m.id,
                "contact_id": m.contact_id,
                "message_type": m.message_type,
                "message_content": m.message_content[:200] + "..." if m.message_content and len(m.message_content) > 200 else m.message_content,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                "got_response": m.got_response,
            }
            for m in messages
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/users/{user_id}/profile")
@limiter.limit(RATE_LIMIT_ADMIN)
def browse_user_profile(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """User's profile data (audit logged)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    log_admin_action(
        db, admin, "view_user_data",
        target_user_id=user_id,
        details={"data_type": "profile"},
        ip_address=get_client_ip(request),
    )

    if not profile:
        return {"profile": None}

    return {
        "profile": {
            "name": profile.name,
            "email": profile.email,
            "linkedin_url": profile.linkedin_url,
            "location": profile.location,
            "school": profile.school,
            "graduation_year": profile.graduation_year,
            "current_title": profile.current_title,
            "years_experience": profile.years_experience,
            "skills": profile.skills,
            "target_roles": profile.target_roles,
            "has_resume": profile.resume_data is not None,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }
    }


# =============================================================================
# 2.4 — Diagnostics
# =============================================================================

@router.get("/diagnostics/empty-profiles")
@limiter.limit(RATE_LIMIT_ADMIN)
def diagnostics_empty_profiles(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Users with 0 contacts AND 0 applications (abandoned signups)."""
    # Subqueries for users who DO have records
    has_contacts = db.query(Contact.user_id).distinct().subquery()
    has_apps = db.query(Application.user_id).distinct().subquery()

    query = (
        db.query(User)
        .outerjoin(has_contacts, User.id == has_contacts.c.user_id)
        .outerjoin(has_apps, User.id == has_apps.c.user_id)
        .filter(has_contacts.c.user_id.is_(None), has_apps.c.user_id.is_(None))
    )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "is_verified": u.is_verified,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/diagnostics/stuck-pipelines")
@limiter.limit(RATE_LIMIT_ADMIN)
def diagnostics_stuck_pipelines(
    request: Request,
    days: int = Query(14, ge=1, le=90),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Users with active applications but no new records in N+ days."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Users with active (non-terminal) applications
    active_statuses = ["saved", "applied", "phone_screen", "technical", "onsite"]
    users_with_active = (
        db.query(Application.user_id)
        .filter(Application.status.in_(active_statuses))
        .distinct()
        .subquery()
    )

    # Users with ANY recent activity (contact, app, company, or message created after cutoff)
    recent_contacts = db.query(Contact.user_id).filter(Contact.created_at >= cutoff)
    recent_apps = db.query(Application.user_id).filter(Application.created_at >= cutoff)
    recent_companies = db.query(Company.user_id).filter(Company.created_at >= cutoff)
    recent_messages = db.query(MessageHistory.user_id).filter(MessageHistory.sent_at >= cutoff)
    recently_active = recent_contacts.union(recent_apps).union(recent_companies).union(recent_messages).subquery()

    query = (
        db.query(User)
        .join(users_with_active, User.id == users_with_active.c.user_id)
        .outerjoin(recently_active, User.id == recently_active.c.user_id)
        .filter(recently_active.c.user_id.is_(None))
    )

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "inactive_days_threshold": days,
    }


@router.get("/diagnostics/unverified")
@limiter.limit(RATE_LIMIT_ADMIN)
def diagnostics_unverified(
    request: Request,
    days: int = Query(7, ge=1, le=365),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Users still unverified after N days (possible email delivery issues)."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = db.query(User).filter(
        User.is_verified == False,
        User.created_at <= cutoff,
    )

    total = query.count()
    users = query.order_by(User.created_at.asc()).offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "days_since_signup": (datetime.utcnow() - u.created_at).days if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "unverified_after_days": days,
    }


# =============================================================================
# 2.5 — Audit Log
# =============================================================================

@router.get("/audit-log")
@limiter.limit(RATE_LIMIT_ADMIN)
def list_audit_log(
    request: Request,
    action: Optional[str] = None,
    admin_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Paginated audit log, filterable by action, admin, or target user."""
    query = db.query(AdminAuditLog)

    if action:
        query = query.filter(AdminAuditLog.action == action)
    if admin_user_id:
        query = query.filter(AdminAuditLog.admin_user_id == admin_user_id)
    if target_user_id:
        query = query.filter(AdminAuditLog.target_user_id == target_user_id)

    total = query.count()
    entries = (
        query.order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # Batch-fetch admin and target user names for display
    all_user_ids = set()
    for e in entries:
        all_user_ids.add(e.admin_user_id)
        if e.target_user_id:
            all_user_ids.add(e.target_user_id)
    user_names = dict(
        db.query(User.id, User.email).filter(User.id.in_(all_user_ids)).all()
    ) if all_user_ids else {}

    return {
        "items": [
            {
                "id": e.id,
                "admin_user_id": e.admin_user_id,
                "admin_email": user_names.get(e.admin_user_id),
                "action": e.action,
                "target_user_id": e.target_user_id,
                "target_email": user_names.get(e.target_user_id) if e.target_user_id else None,
                "details": json.loads(e.details) if e.details else None,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }
