"""
Reusable query helpers for user-scoped data isolation.

These functions eliminate repetitive user_id filtering across routers.
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from .models import MessageTemplate


def user_query(db: Session, model, user):
    """Return a query filtered to the given user's records."""
    return db.query(model).filter(model.user_id == user.id)


def get_owned_or_404(db: Session, model, record_id: int, user, label: str = "Record"):
    """Fetch a record by id and user_id, or raise 404."""
    record = db.query(model).filter(
        model.id == record_id,
        model.user_id == user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return record


def user_templates_query(db: Session, user):
    """Return templates owned by the user OR system templates (user_id IS NULL)."""
    return db.query(MessageTemplate).filter(
        or_(
            MessageTemplate.user_id == user.id,
            MessageTemplate.user_id.is_(None)
        )
    )


def set_user_id(obj, user):
    """Set the user_id attribute on a model instance."""
    obj.user_id = user.id
    return obj
