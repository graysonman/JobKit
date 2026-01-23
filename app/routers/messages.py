"""
Message template management and generation API.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from ..database import get_db
from ..models import MessageTemplate, Contact, UserProfile, MessageHistory
from ..schemas import (
    MessageTemplateCreate, MessageTemplateResponse,
    MessageGenerateRequest, MessageGenerateResponse,
    MessageHistoryCreate, MessageHistoryResponse
)
from ..services.message_generator import generate_message

router = APIRouter()

# --- Template CRUD ---

@router.get("/templates", response_model=List[MessageTemplateResponse])
def list_templates(
    message_type: str = None,
    target_type: str = None,
    db: Session = Depends(get_db)
):
    """List message templates."""
    query = db.query(MessageTemplate)
    if message_type:
        query = query.filter(MessageTemplate.message_type == message_type)
    if target_type:
        query = query.filter(MessageTemplate.target_type == target_type)
    return query.all()


@router.post("/templates", response_model=MessageTemplateResponse)
def create_template(template: MessageTemplateCreate, db: Session = Depends(get_db)):
    """Create a new message template."""
    db_template = MessageTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a message template."""
    db_template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(db_template)
    db.commit()
    return {"message": "Template deleted"}


# --- Message Generation ---

@router.post("/generate", response_model=MessageGenerateResponse)
def generate_message_endpoint(
    request: MessageGenerateRequest,
    db: Session = Depends(get_db)
):
    """Generate a personalized message for a contact."""
    # Get contact
    contact = db.query(Contact).filter(Contact.id == request.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Get user profile
    user_profile = db.query(UserProfile).first()
    if not user_profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first")

    # Get template
    template = None
    if request.template_id:
        template = db.query(MessageTemplate).filter(MessageTemplate.id == request.template_id).first()
    else:
        # Find best matching default template
        # Map contact types to template target types
        target_type_map = {
            'junior_dev': 'developer',
            'senior_dev': 'developer',
            'recruiter': 'recruiter',
            'hiring_manager': 'hiring_manager',
            'other': 'general'
        }
        target_type = target_type_map.get(contact.contact_type, 'general')

        # Check if alumni, use alumni template if so
        if contact.is_alumni:
            target_type = 'alumni'

        template = db.query(MessageTemplate).filter(
            MessageTemplate.message_type == request.message_type,
            MessageTemplate.target_type == target_type,
            MessageTemplate.is_default == True
        ).first()

        if not template:
            template = db.query(MessageTemplate).filter(
                MessageTemplate.message_type == request.message_type,
                MessageTemplate.is_default == True
            ).first()

    if not template:
        raise HTTPException(status_code=400, detail="No suitable template found")

    # Generate message
    message = generate_message(template, contact, user_profile)

    return MessageGenerateResponse(
        message=message,
        subject=template.subject,
        contact_name=contact.name,
        message_type=request.message_type
    )


@router.post("/save-sent", response_model=MessageHistoryResponse)
def save_sent_message(
    data: MessageHistoryCreate,
    db: Session = Depends(get_db)
):
    """Save a message that was sent (for tracking)."""
    history = MessageHistory(
        contact_id=data.contact_id,
        template_id=data.template_id,
        message_type=data.message_type,
        message_content=data.message_content
    )
    db.add(history)

    # Update contact's last_contacted
    contact = db.query(Contact).filter(Contact.id == data.contact_id).first()
    if contact:
        contact.last_contacted = date.today()
        contact.connection_status = "messaged"

    db.commit()
    db.refresh(history)
    return history


@router.get("/history", response_model=List[MessageHistoryResponse])
def get_message_history(
    contact_id: int = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get message history, optionally filtered by contact."""
    query = db.query(MessageHistory)
    if contact_id:
        query = query.filter(MessageHistory.contact_id == contact_id)
    return query.order_by(MessageHistory.sent_at.desc()).offset(skip).limit(limit).all()


# TODO Phase 3: Add AI-powered message generation endpoint
# TODO Phase 3: Add endpoint to rate message effectiveness (got response or not)
