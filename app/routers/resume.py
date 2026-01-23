"""
Resume and cover letter API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from ..database import get_db
from ..models import UserProfile
from ..services.resume_helper import (
    extract_keywords_from_job,
    analyze_resume_match,
    generate_cover_letter,
    suggest_resume_tweaks
)

router = APIRouter()


class JobAnalysisRequest(BaseModel):
    job_description: str


class JobAnalysisResponse(BaseModel):
    required_skills: List[str]
    preferred_skills: List[str]
    experience_level: str
    key_responsibilities: List[str]
    keywords: List[str]


class ResumeMatchRequest(BaseModel):
    resume_text: str
    job_description: str


class ResumeMatchResponse(BaseModel):
    match_score: float
    matching_skills: List[str]
    missing_skills: List[str]
    suggestions: List[str]


class CoverLetterRequest(BaseModel):
    job_description: str
    company_name: str
    role: str
    custom_points: Optional[List[str]] = None


class CoverLetterResponse(BaseModel):
    cover_letter: str


class ResumeTweakSuggestion(BaseModel):
    section: str
    suggestion: str


class ResumeTweaksRequest(BaseModel):
    resume_text: str
    job_description: str


@router.post("/analyze-job", response_model=JobAnalysisResponse)
def analyze_job_description(request: JobAnalysisRequest):
    """Extract requirements from a job description."""
    analysis = extract_keywords_from_job(request.job_description)
    return JobAnalysisResponse(**analysis)


@router.post("/match-resume", response_model=ResumeMatchResponse)
def match_resume_to_job(request: ResumeMatchRequest):
    """Analyze resume match to job."""
    result = analyze_resume_match(request.resume_text, request.job_description)
    return ResumeMatchResponse(**result)


@router.post("/generate-cover-letter", response_model=CoverLetterResponse)
def generate_cover_letter_endpoint(
    request: CoverLetterRequest,
    db: Session = Depends(get_db)
):
    """Generate a cover letter based on user profile and job description."""
    # Get user profile
    profile = db.query(UserProfile).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Please set up your profile first in Settings")

    user_profile = {
        "name": profile.name,
        "current_title": profile.current_title,
        "skills": profile.skills,
        "years_experience": profile.years_experience,
        "resume_summary": profile.resume_summary,
        "elevator_pitch": profile.elevator_pitch
    }

    cover_letter = generate_cover_letter(
        user_profile=user_profile,
        job_description=request.job_description,
        company_name=request.company_name,
        role=request.role,
        custom_points=request.custom_points
    )

    return CoverLetterResponse(cover_letter=cover_letter)


@router.post("/suggest-tweaks", response_model=List[ResumeTweakSuggestion])
def suggest_resume_tweaks_endpoint(request: ResumeTweaksRequest):
    """Get resume improvement suggestions for a specific job."""
    suggestions = suggest_resume_tweaks(request.resume_text, request.job_description)
    return [ResumeTweakSuggestion(**s) for s in suggestions]
