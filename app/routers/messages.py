"""
JobKit - Message template management and generation API.

Endpoints for creating message templates, generating personalized outreach
messages, and tracking sent message history.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from typing import List, Optional
from datetime import date, datetime

from ..database import get_db
from ..models import MessageTemplate, Contact, UserProfile, MessageHistory
from ..schemas import (
    MessageTemplateCreate, MessageTemplateUpdate, MessageTemplateResponse,
    MessageGenerateRequest, MessageGenerateResponse,
    MessageHistoryCreate, MessageHistoryUpdate, MessageHistoryResponse,
    MessageType, TargetType
)
from ..services.message_generator import generate_message

router = APIRouter()


# --- Template CRUD ---

@router.get("/templates", response_model=List[MessageTemplateResponse])
def list_templates(
    message_type: Optional[str] = None,
    target_type: Optional[str] = None,
    is_default: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List message templates with optional filters."""
    query = db.query(MessageTemplate)
    if message_type:
        query = query.filter(MessageTemplate.message_type == message_type)
    if target_type:
        query = query.filter(MessageTemplate.target_type == target_type)
    if is_default is not None:
        query = query.filter(MessageTemplate.is_default == is_default)
    return query.order_by(MessageTemplate.message_type, MessageTemplate.target_type).all()


@router.get("/templates/stats")
def get_template_stats(db: Session = Depends(get_db)):
    """Get template usage and response rate statistics."""
    templates = db.query(MessageTemplate).all()
    stats = []

    for template in templates:
        # Get messages sent using this template
        messages = db.query(MessageHistory).filter(
            MessageHistory.template_id == template.id
        ).all()

        total_sent = len(messages)
        got_response = sum(1 for m in messages if m.got_response)
        response_rate = (got_response / total_sent * 100) if total_sent > 0 else 0

        stats.append({
            "template_id": template.id,
            "template_name": template.name,
            "message_type": template.message_type,
            "target_type": template.target_type,
            "total_sent": total_sent,
            "got_response": got_response,
            "response_rate": round(response_rate, 1)
        })

    # Sort by usage count descending
    stats.sort(key=lambda x: x["total_sent"], reverse=True)
    return stats


@router.get("/templates/{template_id}", response_model=MessageTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific template by ID."""
    template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates", response_model=MessageTemplateResponse)
def create_template(template: MessageTemplateCreate, db: Session = Depends(get_db)):
    """Create a new message template."""
    db_template = MessageTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.patch("/templates/{template_id}", response_model=MessageTemplateResponse)
def update_template(
    template_id: int,
    template: MessageTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a message template."""
    db_template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = template.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_template, key, value)

    db.commit()
    db.refresh(db_template)
    return db_template


@router.post("/templates/{template_id}/duplicate", response_model=MessageTemplateResponse)
def duplicate_template(
    template_id: int,
    new_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Duplicate an existing template."""
    original = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Template not found")

    # Create a copy
    new_template = MessageTemplate(
        name=new_name or f"{original.name} (Copy)",
        message_type=original.message_type,
        target_type=original.target_type,
        subject=original.subject,
        template=original.template,
        is_default=False  # Copies are never default
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return new_template


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a message template."""
    db_template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(db_template)
    db.commit()
    return {"message": "Template deleted"}


@router.get("/templates/export")
def export_templates(db: Session = Depends(get_db)):
    """Export all templates as JSON."""
    templates = db.query(MessageTemplate).all()
    export_data = [
        {
            "name": t.name,
            "message_type": t.message_type,
            "target_type": t.target_type,
            "subject": t.subject,
            "template": t.template,
            "is_default": t.is_default
        }
        for t in templates
    ]
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=templates_export_{date.today()}.json"
        }
    )


@router.post("/templates/import")
def import_templates(
    templates: List[MessageTemplateCreate],
    db: Session = Depends(get_db)
):
    """Import templates from JSON array."""
    imported_count = 0
    for template_data in templates:
        # Check if template with same name exists
        existing = db.query(MessageTemplate).filter(
            MessageTemplate.name == template_data.name
        ).first()
        if not existing:
            db_template = MessageTemplate(**template_data.model_dump())
            db.add(db_template)
            imported_count += 1

    db.commit()
    return {"message": f"Imported {imported_count} templates", "imported": imported_count}


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
        message_type=request.message_type,
        character_count=len(message)
    )


@router.post("/generate-batch")
def generate_messages_batch(
    contact_ids: List[int],
    message_type: MessageType,
    template_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Generate messages for multiple contacts at once."""
    user_profile = db.query(UserProfile).first()
    if not user_profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first")

    results = []
    for contact_id in contact_ids:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if not contact:
            results.append({
                "contact_id": contact_id,
                "error": "Contact not found"
            })
            continue

        try:
            # Use same logic as generate_message_endpoint
            template = None
            if template_id:
                template = db.query(MessageTemplate).filter(MessageTemplate.id == template_id).first()
            else:
                target_type_map = {
                    'junior_dev': 'developer',
                    'senior_dev': 'developer',
                    'recruiter': 'recruiter',
                    'hiring_manager': 'hiring_manager',
                    'other': 'general'
                }
                target_type = target_type_map.get(contact.contact_type, 'general')
                if contact.is_alumni:
                    target_type = 'alumni'

                template = db.query(MessageTemplate).filter(
                    MessageTemplate.message_type == message_type,
                    MessageTemplate.target_type == target_type,
                    MessageTemplate.is_default == True
                ).first()

                if not template:
                    template = db.query(MessageTemplate).filter(
                        MessageTemplate.message_type == message_type,
                        MessageTemplate.is_default == True
                    ).first()

            if template:
                message = generate_message(template, contact, user_profile)
                results.append({
                    "contact_id": contact_id,
                    "contact_name": contact.name,
                    "message": message,
                    "subject": template.subject,
                    "character_count": len(message)
                })
            else:
                results.append({
                    "contact_id": contact_id,
                    "error": "No suitable template found"
                })
        except Exception as e:
            results.append({
                "contact_id": contact_id,
                "error": str(e)
            })

    return results


# --- Message History ---

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
    contact_id: Optional[int] = None,
    message_type: Optional[str] = None,
    got_response: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get message history with optional filters."""
    query = db.query(MessageHistory)
    if contact_id:
        query = query.filter(MessageHistory.contact_id == contact_id)
    if message_type:
        query = query.filter(MessageHistory.message_type == message_type)
    if got_response is not None:
        query = query.filter(MessageHistory.got_response == got_response)
    return query.order_by(MessageHistory.sent_at.desc()).offset(skip).limit(limit).all()


@router.get("/history/stats")
def get_message_history_stats(db: Session = Depends(get_db)):
    """Get message history statistics and response rates."""
    total_sent = db.query(func.count(MessageHistory.id)).scalar() or 0
    got_response = db.query(func.count(MessageHistory.id)).filter(
        MessageHistory.got_response == True
    ).scalar() or 0

    overall_response_rate = (got_response / total_sent * 100) if total_sent > 0 else 0

    # Stats by message type
    by_type = {}
    type_stats = db.query(
        MessageHistory.message_type,
        func.count(MessageHistory.id),
        func.sum(func.cast(MessageHistory.got_response, Integer))
    ).group_by(MessageHistory.message_type).all()

    for msg_type, count, responses in type_stats:
        resp = responses or 0
        by_type[msg_type or "unknown"] = {
            "sent": count,
            "got_response": resp,
            "response_rate": round(resp / count * 100, 1) if count > 0 else 0
        }

    return {
        "total_sent": total_sent,
        "got_response": got_response,
        "overall_response_rate": round(overall_response_rate, 1),
        "by_message_type": by_type
    }


@router.get("/history/{history_id}", response_model=MessageHistoryResponse)
def get_history_entry(history_id: int, db: Session = Depends(get_db)):
    """Get a specific message history entry."""
    history = db.query(MessageHistory).filter(MessageHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History entry not found")
    return history


@router.patch("/history/{history_id}", response_model=MessageHistoryResponse)
def update_history_entry(
    history_id: int,
    update: MessageHistoryUpdate,
    db: Session = Depends(get_db)
):
    """Update a message history entry (e.g., mark as got response)."""
    history = db.query(MessageHistory).filter(MessageHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History entry not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(history, key, value)

    db.commit()
    db.refresh(history)
    return history


@router.patch("/history/{history_id}/response")
def mark_got_response(
    history_id: int,
    response_notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Mark a sent message as having received a response."""
    history = db.query(MessageHistory).filter(MessageHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History entry not found")

    history.got_response = True
    if response_notes:
        history.response_notes = response_notes

    db.commit()
    db.refresh(history)
    return {"message": "Marked as got response", "history_id": history_id}


@router.delete("/history/{history_id}")
def delete_history_entry(history_id: int, db: Session = Depends(get_db)):
    """Delete a message history entry."""
    history = db.query(MessageHistory).filter(MessageHistory.id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="History entry not found")

    db.delete(history)
    db.commit()
    return {"message": "History entry deleted"}


@router.get("/history/export")
def export_message_history(
    contact_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Export message history as JSON."""
    query = db.query(MessageHistory)
    if contact_id:
        query = query.filter(MessageHistory.contact_id == contact_id)

    history = query.order_by(MessageHistory.sent_at.desc()).all()
    export_data = [
        {
            "id": h.id,
            "contact_id": h.contact_id,
            "template_id": h.template_id,
            "message_type": h.message_type,
            "message_content": h.message_content,
            "sent_at": h.sent_at.isoformat() if h.sent_at else None,
            "got_response": h.got_response,
            "response_notes": h.response_notes
        }
        for h in history
    ]

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=message_history_{date.today()}.json"
        }
    )
