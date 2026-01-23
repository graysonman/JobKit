"""
User profile management API.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import UserProfile
from ..schemas import UserProfileBase, UserProfileUpdate, UserProfileResponse

router = APIRouter()

@router.get("/", response_model=UserProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    """Get user profile."""
    profile = db.query(UserProfile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create one first.")
    return profile


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
        return existing
    else:
        # Create new with id=1
        db_profile = UserProfile(id=1, **profile.model_dump())
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return db_profile


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
    return existing
