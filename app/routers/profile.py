"""
JobKit - User profile management API.

Endpoints for managing the user's personal profile, which is used
for personalizing message templates and cover letters.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import date

from ..database import get_db
from ..models import UserProfile
from ..schemas import UserProfileBase, UserProfileUpdate, UserProfileResponse

router = APIRouter()


def calculate_profile_completion(profile: UserProfile) -> int:
    """Calculate profile completion percentage based on filled fields."""
    if not profile:
        return 0

    # Define fields and their weights
    fields = {
        'name': 10,           # Required, high weight
        'email': 10,          # Important for messaging
        'linkedin_url': 5,    # Helpful but optional
        'school': 5,          # For alumni connections
        'graduation_year': 5, # For alumni context
        'current_title': 10,  # Important for positioning
        'years_experience': 5,# Context for messages
        'skills': 15,         # Key for tailoring messages
        'target_roles': 10,   # Important for job search
        'elevator_pitch': 15, # Used in messages
        'resume_summary': 10  # Used in cover letters
    }

    total_weight = sum(fields.values())
    earned_weight = 0

    for field, weight in fields.items():
        value = getattr(profile, field, None)
        if value is not None and value != '':
            earned_weight += weight

    return int((earned_weight / total_weight) * 100)


@router.get("/", response_model=UserProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    """Get user profile with completion percentage."""
    profile = db.query(UserProfile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")

    # Add completion percentage to response
    response = UserProfileResponse.model_validate(profile)
    response.profile_completion = calculate_profile_completion(profile)
    return response


@router.get("/completion")
def get_profile_completion(db: Session = Depends(get_db)):
    """Get detailed profile completion information."""
    profile = db.query(UserProfile).first()
    if not profile:
        return {
            "completion_percentage": 0,
            "filled_fields": [],
            "missing_fields": ["name", "email", "linkedin_url", "school", "graduation_year",
                             "current_title", "years_experience", "skills", "target_roles",
                             "elevator_pitch", "resume_summary"],
            "suggestions": ["Create your profile to get started"]
        }

    # Check each field
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

    # Generate helpful suggestions
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
        "suggestions": suggestions[:3]  # Return top 3 suggestions
    }


@router.post("/", response_model=UserProfileResponse)
def create_profile(profile: UserProfileBase, db: Session = Depends(get_db)):
    """Create or update user profile (only one allowed)."""
    existing = db.query(UserProfile).first()
    if existing:
        # Update existing
        update_data = profile.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        response = UserProfileResponse.model_validate(existing)
        response.profile_completion = calculate_profile_completion(existing)
        return response
    else:
        # Create new with id=1
        db_profile = UserProfile(id=1, **profile.model_dump())
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        response = UserProfileResponse.model_validate(db_profile)
        response.profile_completion = calculate_profile_completion(db_profile)
        return response


@router.patch("/", response_model=UserProfileResponse)
def update_profile(profile: UserProfileUpdate, db: Session = Depends(get_db)):
    """Update user profile."""
    existing = db.query(UserProfile).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")

    update_data = profile.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing, key, value)

    db.commit()
    db.refresh(existing)
    response = UserProfileResponse.model_validate(existing)
    response.profile_completion = calculate_profile_completion(existing)
    return response


@router.delete("/")
def delete_profile(db: Session = Depends(get_db)):
    """Delete user profile."""
    existing = db.query(UserProfile).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(existing)
    db.commit()
    return {"message": "Profile deleted"}


@router.get("/export")
def export_profile(db: Session = Depends(get_db)):
    """Export profile data as JSON."""
    profile = db.query(UserProfile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    export_data = {
        "name": profile.name,
        "email": profile.email,
        "linkedin_url": profile.linkedin_url,
        "school": profile.school,
        "graduation_year": profile.graduation_year,
        "current_title": profile.current_title,
        "years_experience": profile.years_experience,
        "skills": profile.skills,
        "target_roles": profile.target_roles,
        "elevator_pitch": profile.elevator_pitch,
        "resume_summary": profile.resume_summary,
        "exported_at": date.today().isoformat()
    }

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f"attachment; filename=profile_export_{date.today()}.json"
        }
    )


@router.post("/import")
def import_profile(data: dict, db: Session = Depends(get_db)):
    """Import profile data from JSON."""
    # Remove any export metadata
    data.pop("exported_at", None)
    data.pop("id", None)

    existing = db.query(UserProfile).first()
    if existing:
        for key, value in data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return {"message": "Profile updated from import", "profile_id": existing.id}
    else:
        db_profile = UserProfile(id=1, **data)
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return {"message": "Profile created from import", "profile_id": db_profile.id}
