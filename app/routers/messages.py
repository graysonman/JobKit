"""
JobKit - Message template management and generation API.

Endpoints for creating message templates, generating personalized outreach
messages, and tracking sent message history.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer, or_
from typing import List, Optional
from datetime import date, datetime
import logging

from ..database import get_db
from ..models import MessageTemplate, Contact, UserProfile, MessageHistory
from ..schemas import (
    MessageTemplateCreate, MessageTemplateUpdate, MessageTemplateResponse,
    MessageGenerateRequest, MessageGenerateResponse,
    MessageHistoryCreate, MessageHistoryUpdate, MessageHistoryResponse,
    MessageType, TargetType, AIMessageGenerateRequest
)
from ..services.message_generator import generate_message
from ..services.ai_service import ai_service, AIServiceError
from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..query_helpers import user_query, get_owned_or_404, user_templates_query

router = APIRouter()
logger = logging.getLogger("jobkit.messages")


def _get_user_profile(db: Session, user: User):
    return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()


# --- Template CRUD ---

@router.get("/templates", response_model=List[MessageTemplateResponse])
def list_templates(
    message_type: Optional[str] = None,
    target_type: Optional[str] = None,
    is_default: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List message templates with optional filters."""
    query = user_templates_query(db, current_user)
    if message_type:
        query = query.filter(MessageTemplate.message_type == message_type)
    if target_type:
        query = query.filter(MessageTemplate.target_type == target_type)
    if is_default is not None:
        query = query.filter(MessageTemplate.is_default == is_default)
    return query.order_by(MessageTemplate.message_type, MessageTemplate.target_type).all()


@router.get("/templates/stats")
def get_template_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get template usage and response rate statistics."""
    templates = user_templates_query(db, current_user).all()
    stats = []

    for template in templates:
        messages = user_query(db, MessageHistory, current_user).filter(
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

    stats.sort(key=lambda x: x["total_sent"], reverse=True)
    return stats


@router.get("/templates/{template_id}", response_model=MessageTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific template by ID."""
    template = user_templates_query(db, current_user).filter(
        MessageTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates", response_model=MessageTemplateResponse)
def create_template(
    template: MessageTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new message template."""
    db_template = MessageTemplate(**template.model_dump(), user_id=current_user.id)
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


@router.patch("/templates/{template_id}", response_model=MessageTemplateResponse)
def update_template(
    template_id: int,
    template: MessageTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a message template."""
    db_template = user_templates_query(db, current_user).filter(
        MessageTemplate.id == template_id
    ).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Block modification of system templates
    if db_template.user_id is None:
        raise HTTPException(status_code=403, detail="Cannot modify system templates")

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Duplicate an existing template."""
    original = user_templates_query(db, current_user).filter(
        MessageTemplate.id == template_id
    ).first()
    if not original:
        raise HTTPException(status_code=404, detail="Template not found")

    new_template = MessageTemplate(
        name=new_name or f"{original.name} (Copy)",
        message_type=original.message_type,
        target_type=original.target_type,
        subject=original.subject,
        template=original.template,
        is_default=False,
        user_id=current_user.id
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return new_template


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a message template."""
    db_template = user_templates_query(db, current_user).filter(
        MessageTemplate.id == template_id
    ).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")

    if db_template.user_id is None:
        raise HTTPException(status_code=403, detail="Cannot delete system templates")

    db.delete(db_template)
    db.commit()
    return {"message": "Template deleted"}


@router.get("/templates/export")
def export_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export all templates as JSON."""
    templates = user_templates_query(db, current_user).all()
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Import templates from JSON array."""
    imported_count = 0
    for template_data in templates:
        existing = user_query(db, MessageTemplate, current_user).filter(
            MessageTemplate.name == template_data.name
        ).first()
        if not existing:
            db_template = MessageTemplate(**template_data.model_dump(), user_id=current_user.id)
            db.add(db_template)
            imported_count += 1

    db.commit()
    return {"message": f"Imported {imported_count} templates", "imported": imported_count}


# --- Message Generation ---

@router.post("/generate", response_model=MessageGenerateResponse)
def generate_message_endpoint(
    request: MessageGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a personalized message for a contact."""
    contact = get_owned_or_404(db, Contact, request.contact_id, current_user, "Contact")

    user_profile = _get_user_profile(db, current_user)
    if not user_profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first")

    template = None
    if request.template_id:
        template = user_templates_query(db, current_user).filter(
            MessageTemplate.id == request.template_id
        ).first()
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

        template = user_templates_query(db, current_user).filter(
            MessageTemplate.message_type == request.message_type,
            MessageTemplate.target_type == target_type,
            MessageTemplate.is_default == True
        ).first()

        if not template:
            template = user_templates_query(db, current_user).filter(
                MessageTemplate.message_type == request.message_type,
                MessageTemplate.is_default == True
            ).first()

    if not template:
        raise HTTPException(status_code=400, detail="No suitable template found")

    message = generate_message(template, contact, user_profile)

    return MessageGenerateResponse(
        message=message,
        subject=template.subject,
        contact_name=contact.name,
        message_type=request.message_type,
        character_count=len(message)
    )


@router.post("/generate-ai", response_model=MessageGenerateResponse)
async def generate_message_ai_endpoint(
    request: AIMessageGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a personalized message using AI (Ollama).

    Falls back to template-based generation if AI is unavailable.
    """
    contact = get_owned_or_404(db, Contact, request.contact_id, current_user, "Contact")

    user_profile = _get_user_profile(db, current_user)
    if not user_profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first")

    # Try AI generation first
    try:
        if await ai_service.is_available():
            message, ai_generated = await ai_service.generate_message_ai(
                contact=contact,
                profile=user_profile,
                message_type=request.message_type,
                context=request.context
            )
            return MessageGenerateResponse(
                message=message,
                subject=None,
                contact_name=contact.name,
                message_type=request.message_type,
                character_count=len(message),
                ai_generated=True
            )
    except Exception as e:
        logger.warning(f"AI message generation failed, falling back to template: {e}")
        pass  # Fall through to template-based generation

    # Fallback: template-based generation
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

    template = user_templates_query(db, current_user).filter(
        MessageTemplate.message_type == request.message_type,
        MessageTemplate.target_type == target_type,
        MessageTemplate.is_default == True
    ).first()

    if not template:
        template = user_templates_query(db, current_user).filter(
            MessageTemplate.message_type == request.message_type,
            MessageTemplate.is_default == True
        ).first()

    if not template:
        raise HTTPException(
            status_code=400,
            detail="AI is unavailable and no suitable template found for fallback"
        )

    message = generate_message(template, contact, user_profile)
    return MessageGenerateResponse(
        message=message,
        subject=template.subject,
        contact_name=contact.name,
        message_type=request.message_type,
        character_count=len(message),
        ai_generated=False
    )


@router.post("/generate-batch")
def generate_messages_batch(
    contact_ids: List[int],
    message_type: MessageType,
    template_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate messages for multiple contacts at once."""
    user_profile = _get_user_profile(db, current_user)
    if not user_profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first")

    results = []
    for contact_id in contact_ids:
        contact = db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.user_id == current_user.id
        ).first()
        if not contact:
            results.append({"contact_id": contact_id, "error": "Contact not found"})
            continue

        try:
            template = None
            if template_id:
                template = user_templates_query(db, current_user).filter(
                    MessageTemplate.id == template_id
                ).first()
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

                template = user_templates_query(db, current_user).filter(
                    MessageTemplate.message_type == message_type,
                    MessageTemplate.target_type == target_type,
                    MessageTemplate.is_default == True
                ).first()

                if not template:
                    template = user_templates_query(db, current_user).filter(
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
                results.append({"contact_id": contact_id, "error": "No suitable template found"})
        except Exception as e:
            results.append({"contact_id": contact_id, "error": str(e)})

    return results


# --- Message History ---

@router.post("/save-sent", response_model=MessageHistoryResponse)
def save_sent_message(
    data: MessageHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Save a message that was sent (for tracking)."""
    # Verify contact ownership
    get_owned_or_404(db, Contact, data.contact_id, current_user, "Contact")

    history = MessageHistory(
        contact_id=data.contact_id,
        user_id=current_user.id,
        template_id=data.template_id,
        message_type=data.message_type,
        message_content=data.message_content
    )
    db.add(history)

    contact = db.query(Contact).filter(
        Contact.id == data.contact_id,
        Contact.user_id == current_user.id
    ).first()
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get message history with optional filters."""
    query = user_query(db, MessageHistory, current_user)
    if contact_id:
        query = query.filter(MessageHistory.contact_id == contact_id)
    if message_type:
        query = query.filter(MessageHistory.message_type == message_type)
    if got_response is not None:
        query = query.filter(MessageHistory.got_response == got_response)
    return query.order_by(MessageHistory.sent_at.desc()).offset(skip).limit(limit).all()


@router.get("/history/stats")
def get_message_history_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get message history statistics and response rates."""
    base = user_query(db, MessageHistory, current_user)
    total_sent = base.count()
    got_response = base.filter(MessageHistory.got_response == True).count()

    overall_response_rate = (got_response / total_sent * 100) if total_sent > 0 else 0

    by_type = {}
    type_stats = base.with_entities(
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
def get_history_entry(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific message history entry."""
    return get_owned_or_404(db, MessageHistory, history_id, current_user, "History entry")


@router.patch("/history/{history_id}", response_model=MessageHistoryResponse)
def update_history_entry(
    history_id: int,
    update: MessageHistoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a message history entry (e.g., mark as got response)."""
    history = get_owned_or_404(db, MessageHistory, history_id, current_user, "History entry")

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark a sent message as having received a response."""
    history = get_owned_or_404(db, MessageHistory, history_id, current_user, "History entry")

    history.got_response = True
    if response_notes:
        history.response_notes = response_notes

    db.commit()
    db.refresh(history)
    return {"message": "Marked as got response", "history_id": history_id}


@router.delete("/history/{history_id}")
def delete_history_entry(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a message history entry."""
    history = get_owned_or_404(db, MessageHistory, history_id, current_user, "History entry")
    db.delete(history)
    db.commit()
    return {"message": "History entry deleted"}


@router.get("/history/export")
def export_message_history(
    contact_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export message history as JSON."""
    query = user_query(db, MessageHistory, current_user)
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


# --- Message Analysis & Tools ---

@router.post("/validate-length")
def validate_message_length_endpoint(
    message: str,
    platform: str = Query("linkedin_connection", pattern="^(linkedin_connection|linkedin_inmail|linkedin_message|email_subject|twitter_dm)$")
):
    """Validate message length for a specific platform."""
    from ..services.message_generator import validate_message_length
    return validate_message_length(message, platform)


@router.post("/detect-overused-phrases")
def detect_overused_phrases_endpoint(message: str):
    """Detect overused phrases in a message."""
    from ..services.message_generator import detect_overused_phrases
    phrases = detect_overused_phrases(message)
    return {
        "overused_phrases": phrases,
        "count": len(phrases),
        "message": f"Found {len(phrases)} overused phrase(s)" if phrases else "No overused phrases detected"
    }


@router.post("/suggest-improvements")
def suggest_improvements_endpoint(message: str):
    """Get suggestions to improve a message."""
    from ..services.message_generator import suggest_message_improvements, detect_overused_phrases
    suggestions = suggest_message_improvements(message)
    overused = detect_overused_phrases(message)
    return {
        "suggestions": suggestions,
        "overused_phrases": overused,
        "character_count": len(message)
    }


@router.post("/generate-variations")
def generate_variations_endpoint(
    contact_id: int,
    template_id: int,
    count: int = Query(3, ge=2, le=5),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate multiple variations of a message for A/B testing."""
    from ..services.message_generator import generate_variations

    contact = get_owned_or_404(db, Contact, contact_id, current_user, "Contact")

    template = user_templates_query(db, current_user).filter(
        MessageTemplate.id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    user_profile = _get_user_profile(db, current_user)
    if not user_profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first")

    variations = generate_variations(template, contact, user_profile, count)
    return {
        "contact_name": contact.name,
        "template_name": template.name,
        "variations": variations
    }


@router.post("/generate-followup-sequence")
def generate_followup_sequence_endpoint(
    contact_id: int,
    context: str = Query("general", pattern="^(general|application|meeting|referral)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a sequence of follow-up messages (day 3, 7, 14)."""
    from ..services.message_generator import generate_followup_sequence

    contact = get_owned_or_404(db, Contact, contact_id, current_user, "Contact")

    user_profile = _get_user_profile(db, current_user)
    if not user_profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first")

    sequence = generate_followup_sequence(contact, user_profile, context)
    return {
        "contact_name": contact.name,
        "context": context,
        "sequence": sequence
    }


@router.get("/platform-limits")
def get_platform_limits():
    """Get character limits for different messaging platforms."""
    from ..services.message_generator import PLATFORM_LIMITS
    return {
        "platforms": PLATFORM_LIMITS,
        "descriptions": {
            "linkedin_connection": "LinkedIn connection request note",
            "linkedin_inmail": "LinkedIn InMail message",
            "linkedin_message": "LinkedIn direct message",
            "email_subject": "Email subject line",
            "twitter_dm": "Twitter direct message"
        }
    }
