"""
JobKit - CRUD API for networking contacts.

Endpoints for managing professional networking contacts including
recruiters, developers, hiring managers, and alumni connections.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import date, timedelta

from ..database import get_db
from ..models import Contact, Interaction, MessageHistory
from ..schemas import (
    ContactCreate, ContactUpdate, ContactResponse,
    InteractionCreate, InteractionResponse,
    ContactStats, MessageHistoryResponse
)

router = APIRouter()


@router.get("/", response_model=List[ContactResponse])
def list_contacts(
    skip: int = 0,
    limit: int = 100,
    contact_type: Optional[str] = None,
    is_alumni: Optional[bool] = None,
    connection_status: Optional[str] = None,
    company: Optional[str] = None,
    needs_follow_up: bool = False,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(None, pattern="^(name|company|created_at|last_contacted|next_follow_up)$"),
    sort_order: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """List contacts with optional filters, search, and sorting."""
    query = db.query(Contact)

    # Filters
    if contact_type:
        query = query.filter(Contact.contact_type == contact_type)
    if is_alumni is not None:
        query = query.filter(Contact.is_alumni == is_alumni)
    if connection_status:
        query = query.filter(Contact.connection_status == connection_status)
    if company:
        query = query.filter(Contact.company.ilike(f"%{company}%"))
    if needs_follow_up:
        query = query.filter(Contact.next_follow_up <= date.today())

    # Search across multiple fields
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Contact.name.ilike(search_term),
                Contact.company.ilike(search_term),
                Contact.email.ilike(search_term),
                Contact.role.ilike(search_term),
                Contact.notes.ilike(search_term)
            )
        )

    # Sorting
    if sort_by:
        sort_column = getattr(Contact, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(Contact.created_at.desc())

    return query.offset(skip).limit(limit).all()


@router.get("/stats", response_model=ContactStats)
def get_contact_stats(db: Session = Depends(get_db)):
    """Get contact statistics."""
    total = db.query(func.count(Contact.id)).scalar() or 0

    # Count by type
    by_type = {}
    type_counts = db.query(Contact.contact_type, func.count(Contact.id)).group_by(Contact.contact_type).all()
    for contact_type, count in type_counts:
        by_type[contact_type or "unspecified"] = count

    # Count by status
    by_status = {}
    status_counts = db.query(Contact.connection_status, func.count(Contact.id)).group_by(Contact.connection_status).all()
    for status, count in status_counts:
        by_status[status] = count

    # Needs follow-up
    needs_follow_up = db.query(func.count(Contact.id)).filter(
        Contact.next_follow_up <= date.today()
    ).scalar() or 0

    # Contacted this week
    week_ago = date.today() - timedelta(days=7)
    contacted_this_week = db.query(func.count(Contact.id)).filter(
        Contact.last_contacted >= week_ago
    ).scalar() or 0

    # Contacted this month
    month_ago = date.today() - timedelta(days=30)
    contacted_this_month = db.query(func.count(Contact.id)).filter(
        Contact.last_contacted >= month_ago
    ).scalar() or 0

    return ContactStats(
        total=total,
        by_type=by_type,
        by_status=by_status,
        needs_follow_up=needs_follow_up,
        contacted_this_week=contacted_this_week,
        contacted_this_month=contacted_this_month
    )


@router.get("/upcoming-followups", response_model=List[ContactResponse])
def get_upcoming_followups(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get contacts with follow-ups due in the next N days."""
    future_date = date.today() + timedelta(days=days)
    contacts = db.query(Contact).filter(
        Contact.next_follow_up <= future_date,
        Contact.next_follow_up >= date.today()
    ).order_by(Contact.next_follow_up.asc()).all()
    return contacts


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a specific contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/", response_model=ContactResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    """Create a new contact."""
    db_contact = Contact(**contact.model_dump())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)):
    """Update a contact."""
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = contact.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_contact, key, value)

    db.commit()
    db.refresh(db_contact)
    return db_contact


@router.delete("/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """Delete a contact."""
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    db.delete(db_contact)
    db.commit()
    return {"message": "Contact deleted"}


@router.patch("/{contact_id}/snooze")
def snooze_followup(
    contact_id: int,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Snooze a contact's follow-up date."""
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    db_contact.next_follow_up = date.today() + timedelta(days=days)
    db.commit()
    db.refresh(db_contact)
    return {"message": f"Follow-up snoozed to {db_contact.next_follow_up}"}


# --- Interaction endpoints ---

@router.get("/{contact_id}/interactions", response_model=List[InteractionResponse])
def get_contact_interactions(
    contact_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get interactions for a contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    interactions = db.query(Interaction).filter(
        Interaction.contact_id == contact_id
    ).order_by(Interaction.interaction_date.desc()).limit(limit).all()
    return interactions


@router.post("/{contact_id}/interactions", response_model=InteractionResponse)
def create_interaction(
    contact_id: int,
    interaction: InteractionCreate,
    db: Session = Depends(get_db)
):
    """Log an interaction with a contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    db_interaction = Interaction(
        contact_id=contact_id,
        interaction_type=interaction.interaction_type,
        interaction_date=interaction.interaction_date,
        notes=interaction.notes,
        follow_up_needed=interaction.follow_up_needed,
        follow_up_date=interaction.follow_up_date
    )
    db.add(db_interaction)

    # Update contact's last_contacted
    contact.last_contacted = interaction.interaction_date

    # Update follow-up date if specified
    if interaction.follow_up_needed and interaction.follow_up_date:
        contact.next_follow_up = interaction.follow_up_date

    db.commit()
    db.refresh(db_interaction)
    return db_interaction


# --- Message history endpoint ---

@router.get("/{contact_id}/messages", response_model=List[MessageHistoryResponse])
def get_contact_messages(
    contact_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get message history for a contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    messages = db.query(MessageHistory).filter(
        MessageHistory.contact_id == contact_id
    ).order_by(MessageHistory.sent_at.desc()).limit(limit).all()
    return messages


# --- Bulk operations ---

@router.post("/bulk", response_model=List[ContactResponse])
def bulk_create_contacts(
    contacts: List[ContactCreate],
    db: Session = Depends(get_db)
):
    """Create multiple contacts at once."""
    created_contacts = []
    for contact_data in contacts:
        db_contact = Contact(**contact_data.model_dump())
        db.add(db_contact)
        created_contacts.append(db_contact)

    db.commit()
    for contact in created_contacts:
        db.refresh(contact)

    return created_contacts
