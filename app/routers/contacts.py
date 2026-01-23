"""
CRUD API for networking contacts.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from ..database import get_db
from ..models import Contact
from ..schemas import ContactCreate, ContactUpdate, ContactResponse

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
    db: Session = Depends(get_db)
):
    """List contacts with optional filters."""
    query = db.query(Contact)

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

    # TODO Phase 6: Add sorting options (by name, company, last_contacted, etc.)
    # TODO Phase 6: Add search across name, company, notes

    return query.offset(skip).limit(limit).all()


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


# TODO Phase 2: Add bulk import endpoint (CSV)
# TODO Phase 6: Add /contacts/{id}/interactions endpoint
# TODO Phase 6: Add /contacts/{id}/messages endpoint for message history
