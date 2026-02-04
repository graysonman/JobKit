"""
JobKit - User profile management API.

Endpoints for managing the user's personal profile, which is used
for personalizing message templates and cover letters.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import date

from ..database import get_db
from ..models import UserProfile
from ..schemas import UserProfileBase, UserProfileUpdate, UserProfileResponse, StructuredResume
from ..auth.dependencies import get_current_active_user
from ..auth.models import User

router = APIRouter()


def serialize_resume_data(resume_data: StructuredResume) -> str:
    """Convert StructuredResume to JSON string for database storage."""
    if resume_data is None:
        return None
    return json.dumps(resume_data.model_dump())


def deserialize_resume_data(json_str: str) -> StructuredResume:
    """Convert JSON string from database to StructuredResume object."""
    if json_str is None:
        return None
    try:
        data = json.loads(json_str)
        return StructuredResume(**data)
    except (json.JSONDecodeError, Exception):
        return None


def profile_to_response(profile: UserProfile) -> UserProfileResponse:
    """Convert database profile to response model with resume_data deserialization."""
    data = {
        "id": profile.id,
        "name": profile.name,
        "email": profile.email,
        "phone_number": profile.phone_number,
        "linkedin_url": profile.linkedin_url,
        "location": profile.location,
        "school": profile.school,
        "graduation_year": profile.graduation_year,
        "current_title": profile.current_title,
        "years_experience": profile.years_experience,
        "skills": profile.skills,
        "target_roles": profile.target_roles,
        "preferred_locations": profile.preferred_locations,
        "salary_expectations": profile.salary_expectations,
        "elevator_pitch": profile.elevator_pitch,
        "resume_summary": profile.resume_summary,
        "resume_file_path": profile.resume_file_path,
        "resume_data": deserialize_resume_data(profile.resume_data),
        "updated_at": profile.updated_at,
        "profile_completion": calculate_profile_completion(profile)
    }
    return UserProfileResponse(**data)


def calculate_profile_completion(profile: UserProfile) -> int:
    """Calculate profile completion percentage based on filled fields."""
    if not profile:
        return 0

    fields = {
        'name': 10,
        'email': 10,
        'linkedin_url': 5,
        'school': 5,
        'graduation_year': 5,
        'current_title': 10,
        'years_experience': 5,
        'skills': 15,
        'target_roles': 10,
        'elevator_pitch': 15,
        'resume_summary': 10
    }

    total_weight = sum(fields.values())
    earned_weight = 0

    for field, weight in fields.items():
        value = getattr(profile, field, None)
        if value is not None and value != '':
            earned_weight += weight

    return int((earned_weight / total_weight) * 100)


def _get_user_profile(db: Session, user: User):
    """Get the profile for the current user."""
    return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()


@router.get("/", response_model=UserProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user profile with completion percentage."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")

    return profile_to_response(profile)


@router.get("/completion")
def get_profile_completion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed profile completion information."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        return {
            "completion_percentage": 0,
            "filled_fields": [],
            "missing_fields": ["name", "email", "linkedin_url", "school", "graduation_year",
                             "current_title", "years_experience", "skills", "target_roles",
                             "elevator_pitch", "resume_summary"],
            "suggestions": ["Create your profile to get started"]
        }

    fields = ['name', 'email', 'linkedin_url', 'school', 'graduation_year',
              'current_title', 'years_experience', 'skills', 'target_roles',
              'elevator_pitch', 'resume_summary']

    filled = []
    missing = []
    suggestions = []

    for field in fields:
        value = getattr(profile, field, None)
        if value is not None and value != '':
            filled.append(field)
        else:
            missing.append(field)

    if 'name' in missing:
        suggestions.append("Add your name - it's required for personalized messages")
    if 'skills' in missing:
        suggestions.append("Add your skills to tailor messages to your expertise")
    if 'elevator_pitch' in missing:
        suggestions.append("Write an elevator pitch for use in InMail messages")
    if 'target_roles' in missing:
        suggestions.append("Specify your target roles to help with job matching")
    if 'school' in missing:
        suggestions.append("Add your school to leverage alumni connections")

    return {
        "completion_percentage": calculate_profile_completion(profile),
        "filled_fields": filled,
        "missing_fields": missing,
        "suggestions": suggestions[:3]
    }


@router.post("/", response_model=UserProfileResponse)
def create_profile(
    profile: UserProfileBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create or update user profile (only one allowed per user)."""
    existing = _get_user_profile(db, current_user)

    # Prepare data, converting resume_data to JSON string
    update_data = profile.model_dump(exclude_unset=True)
    if 'resume_data' in update_data and update_data['resume_data'] is not None:
        update_data['resume_data'] = serialize_resume_data(profile.resume_data)

    if existing:
        for key, value in update_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return profile_to_response(existing)
    else:
        db_profile = UserProfile(user_id=current_user.id, **update_data)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return profile_to_response(db_profile)


@router.patch("/", response_model=UserProfileResponse)
def update_profile(
    profile: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update user profile."""
    existing = _get_user_profile(db, current_user)
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")

    update_data = profile.model_dump(exclude_unset=True)

    if 'resume_data' in update_data and update_data['resume_data'] is not None:
        update_data['resume_data'] = serialize_resume_data(profile.resume_data)

    for key, value in update_data.items():
        setattr(existing, key, value)

    db.commit()
    db.refresh(existing)
    return profile_to_response(existing)


@router.delete("/")
def delete_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete user profile."""
    existing = _get_user_profile(db, current_user)
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(existing)
    db.commit()
    return {"message": "Profile deleted"}


# --- Resume Data Endpoints ---

@router.get("/resume", response_model=StructuredResume)
def get_resume_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the user's structured resume data."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")

    resume_data = deserialize_resume_data(profile.resume_data)
    if not resume_data:
        return StructuredResume()

    return resume_data


@router.put("/resume", response_model=StructuredResume)
def update_resume_data(
    resume: StructuredResume,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update the user's structured resume data."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")

    profile.resume_data = serialize_resume_data(resume)

    text_parts = []
    if resume.summary:
        text_parts.append(resume.summary)
    if resume.skills:
        text_parts.append(f"Skills: {', '.join(resume.skills)}")
    if text_parts:
        profile.resume_summary = "\n\n".join(text_parts)

    db.commit()
    db.refresh(profile)

    return deserialize_resume_data(profile.resume_data)


@router.get("/resume/text")
def get_resume_as_text(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the resume as formatted plain text."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    resume_data = deserialize_resume_data(profile.resume_data)
    if not resume_data:
        return {"text": profile.resume_summary or ""}

    lines = []

    if profile.name:
        lines.append(profile.name.upper())
        lines.append("")

    if resume_data.summary:
        lines.append("SUMMARY")
        lines.append(resume_data.summary)
        lines.append("")

    if resume_data.experience:
        lines.append("EXPERIENCE")
        for exp in resume_data.experience:
            date_range = f"{exp.start_date or ''} - {exp.end_date or 'Present'}"
            lines.append(f"{exp.title} at {exp.company}")
            lines.append(f"{date_range}" + (f" | {exp.location}" if exp.location else ""))
            for bullet in exp.bullets:
                lines.append(f"  • {bullet}")
            lines.append("")

    if resume_data.education:
        lines.append("EDUCATION")
        for edu in resume_data.education:
            degree_line = f"{edu.degree or ''} {edu.field or ''}".strip()
            lines.append(f"{edu.school}" + (f" - {degree_line}" if degree_line else ""))
            if edu.year:
                lines.append(f"  {edu.year}")
            lines.append("")

    if resume_data.skills:
        lines.append("SKILLS")
        lines.append(", ".join(resume_data.skills))
        lines.append("")

    if resume_data.projects:
        lines.append("PROJECTS")
        for proj in resume_data.projects:
            lines.append(proj.name)
            if proj.description:
                lines.append(f"  {proj.description}")
            if proj.technologies:
                lines.append(f"  Technologies: {', '.join(proj.technologies)}")
            lines.append("")

    if resume_data.certifications:
        lines.append("CERTIFICATIONS")
        for cert in resume_data.certifications:
            lines.append(f"  • {cert}")

    return {"text": "\n".join(lines)}


@router.get("/export")
def export_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Export profile data as JSON."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    resume_data = deserialize_resume_data(profile.resume_data)

    export_data = {
        "name": profile.name,
        "email": profile.email,
        "phone_number": profile.phone_number,
        "linkedin_url": profile.linkedin_url,
        "location": profile.location,
        "school": profile.school,
        "graduation_year": profile.graduation_year,
        "current_title": profile.current_title,
        "years_experience": profile.years_experience,
        "skills": profile.skills,
        "target_roles": profile.target_roles,
        "preferred_locations": profile.preferred_locations,
        "salary_expectations": profile.salary_expectations,
        "elevator_pitch": profile.elevator_pitch,
        "resume_summary": profile.resume_summary,
        "resume_file_path": profile.resume_file_path,
        "resume_data": resume_data.model_dump() if resume_data else None,
        "exported_at": date.today().isoformat()
    }

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=profile_export_{date.today()}.json"
        }
    )


@router.post("/import")
def import_profile(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Import profile data from JSON."""
    data.pop("exported_at", None)
    data.pop("id", None)

    if 'resume_data' in data and data['resume_data'] is not None:
        try:
            resume = StructuredResume(**data['resume_data'])
            data['resume_data'] = serialize_resume_data(resume)
        except Exception:
            data['resume_data'] = None

    existing = _get_user_profile(db, current_user)
    if existing:
        for key, value in data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return {"message": "Profile updated from import", "profile_id": existing.id}
    else:
        db_profile = UserProfile(user_id=current_user.id, **data)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return {"message": "Profile created from import", "profile_id": db_profile.id}
