"""
JobKit - Resume and cover letter API endpoints.

Endpoints for analyzing job descriptions, matching resumes to jobs,
generating cover letters, and suggesting resume improvements.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import re

from ..database import get_db
from ..models import UserProfile, Application
from ..services.resume_helper import (
    extract_keywords_from_job,
    analyze_resume_match,
    generate_cover_letter,
    suggest_resume_tweaks
)

router = APIRouter()


# --- Request/Response Models ---

class JobAnalysisRequest(BaseModel):
    job_description: str = Field(..., min_length=50)


class JobAnalysisResponse(BaseModel):
    required_skills: List[str]
    preferred_skills: List[str]
    experience_level: str
    key_responsibilities: List[str]
    keywords: List[str]


class ResumeMatchRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)
    job_description: str = Field(..., min_length=50)


class ResumeMatchResponse(BaseModel):
    match_score: float
    matching_skills: List[str]
    missing_skills: List[str]
    suggestions: List[str]


class CoverLetterRequest(BaseModel):
    job_description: str = Field(..., min_length=50)
    company_name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    custom_points: Optional[List[str]] = None
    tone: Optional[str] = "professional"  # professional, conversational, enthusiastic, formal
    length: Optional[str] = "medium"  # short, medium, detailed


class CoverLetterResponse(BaseModel):
    cover_letter: str
    word_count: int
    character_count: int


class ResumeTweakSuggestion(BaseModel):
    section: str
    suggestion: str
    priority: str = "medium"


class ResumeTweaksRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)
    job_description: str = Field(..., min_length=50)


class ATSCheckRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)


class ATSCheckResponse(BaseModel):
    score: int
    issues: List[str]
    recommendations: List[str]
    format_warnings: List[str]


class KeywordDensityRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)
    job_description: str = Field(..., min_length=50)


class KeywordDensityResponse(BaseModel):
    job_keywords: List[str]
    found_keywords: List[str]
    missing_keywords: List[str]
    density_score: float
    suggestions: List[str]


# --- Job Analysis Endpoints ---

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


# --- Cover Letter Endpoints ---

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
        custom_points=request.custom_points,
        tone=request.tone or "professional",
        length=request.length or "medium"
    )

    return CoverLetterResponse(
        cover_letter=cover_letter,
        word_count=len(cover_letter.split()),
        character_count=len(cover_letter)
    )


@router.post("/generate-cover-letter-for-application", response_model=CoverLetterResponse)
def generate_cover_letter_for_application(
    application_id: int,
    custom_points: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """Generate a cover letter for a specific application."""
    # Get application
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.job_description:
        raise HTTPException(status_code=400, detail="Application has no job description")

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
        job_description=application.job_description,
        company_name=application.company_name,
        role=application.role,
        custom_points=custom_points
    )

    return CoverLetterResponse(
        cover_letter=cover_letter,
        word_count=len(cover_letter.split()),
        character_count=len(cover_letter)
    )


# --- Resume Optimization Endpoints ---

@router.post("/suggest-tweaks", response_model=List[ResumeTweakSuggestion])
def suggest_resume_tweaks_endpoint(request: ResumeTweaksRequest):
    """Get resume improvement suggestions for a specific job."""
    suggestions = suggest_resume_tweaks(request.resume_text, request.job_description)
    return [ResumeTweakSuggestion(**s) for s in suggestions]


@router.post("/ats-check", response_model=ATSCheckResponse)
def check_ats_compatibility(request: ATSCheckRequest):
    """Check resume for ATS (Applicant Tracking System) compatibility."""
    resume_text = request.resume_text
    issues = []
    recommendations = []
    format_warnings = []
    score = 100

    # Check for common ATS issues

    # 1. Contact information
    if not re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text):
        issues.append("No email address detected")
        score -= 10

    if not re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text):
        issues.append("No phone number detected")
        score -= 5

    # 2. Section headings
    common_sections = ['experience', 'education', 'skills', 'summary', 'objective', 'work history']
    found_sections = sum(1 for s in common_sections if s.lower() in resume_text.lower())
    if found_sections < 2:
        issues.append("Missing standard section headings (Experience, Education, Skills)")
        recommendations.append("Add clear section headings like 'Experience', 'Education', 'Skills'")
        score -= 15

    # 3. Length check
    word_count = len(resume_text.split())
    if word_count < 200:
        issues.append(f"Resume seems too short ({word_count} words)")
        recommendations.append("Add more detail to your experience and skills sections")
        score -= 10
    elif word_count > 1500:
        format_warnings.append(f"Resume may be too long ({word_count} words) - consider condensing")
        score -= 5

    # 4. Check for problematic characters
    if re.search(r'[^\x00-\x7F]+', resume_text):
        format_warnings.append("Contains special characters that may not parse correctly")
        score -= 5

    # 5. Check for tables/columns indicators
    if '|' in resume_text or '\t\t' in resume_text:
        format_warnings.append("May contain tables or columns - ATS often struggles with these")
        recommendations.append("Use a single-column format for better ATS parsing")
        score -= 10

    # 6. Check for action verbs
    action_verbs = ['managed', 'developed', 'created', 'led', 'implemented', 'designed',
                   'achieved', 'improved', 'built', 'launched', 'increased', 'reduced']
    found_verbs = sum(1 for v in action_verbs if v.lower() in resume_text.lower())
    if found_verbs < 3:
        recommendations.append("Use more action verbs (managed, developed, achieved, etc.)")
        score -= 5

    # 7. Check for quantifiable achievements
    if not re.search(r'\d+%|\$\d+|\d+ years?|\d+ projects?|\d+ team', resume_text.lower()):
        recommendations.append("Add quantifiable achievements (percentages, dollar amounts, numbers)")
        score -= 5

    # Ensure score doesn't go below 0
    score = max(0, score)

    return ATSCheckResponse(
        score=score,
        issues=issues,
        recommendations=recommendations,
        format_warnings=format_warnings
    )


@router.post("/keyword-density", response_model=KeywordDensityResponse)
def analyze_keyword_density(request: KeywordDensityRequest):
    """Analyze how well resume keywords match job description."""
    resume_lower = request.resume_text.lower()
    job_lower = request.job_description.lower()

    # Extract important keywords from job description
    # Common filler words to ignore
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
                 'our', 'your', 'their', 'this', 'that', 'these', 'those', 'it',
                 'we', 'you', 'they', 'he', 'she', 'who', 'which', 'what', 'where',
                 'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
                 'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same',
                 'than', 'too', 'very', 'just', 'also', 'work', 'ability', 'experience'}

    # Extract words from job description
    job_words = re.findall(r'\b[a-z]+\b', job_lower)
    job_keywords = [w for w in job_words if w not in stop_words and len(w) > 2]

    # Count frequency and get top keywords
    keyword_freq = {}
    for word in job_keywords:
        keyword_freq[word] = keyword_freq.get(word, 0) + 1

    # Get top 20 most frequent keywords
    top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    job_keywords_list = [k for k, v in top_keywords]

    # Check which keywords are in resume
    found = []
    missing = []
    for keyword in job_keywords_list:
        if keyword in resume_lower:
            found.append(keyword)
        else:
            missing.append(keyword)

    # Calculate density score
    density_score = len(found) / len(job_keywords_list) * 100 if job_keywords_list else 0

    # Generate suggestions
    suggestions = []
    if density_score < 50:
        suggestions.append("Your resume may not pass ATS keyword filters - add more job-specific terms")
    if missing:
        suggestions.append(f"Consider adding these missing keywords: {', '.join(missing[:5])}")
    if density_score >= 80:
        suggestions.append("Good keyword coverage! Focus on showcasing impact and achievements")

    return KeywordDensityResponse(
        job_keywords=job_keywords_list,
        found_keywords=found,
        missing_keywords=missing,
        density_score=round(density_score, 1),
        suggestions=suggestions
    )


# --- Analysis for Applications ---

@router.post("/analyze-for-application")
def analyze_resume_for_application(
    application_id: int,
    resume_text: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Comprehensive resume analysis for a specific job application."""
    # Get application
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if not application.job_description:
        raise HTTPException(status_code=400, detail="Application has no job description")

    # Get resume text from profile if not provided
    if not resume_text:
        profile = db.query(UserProfile).first()
        if not profile or not profile.resume_summary:
            raise HTTPException(status_code=400, detail="No resume text provided and no resume summary in profile")
        resume_text = profile.resume_summary

    # Run all analyses
    job_analysis = extract_keywords_from_job(application.job_description)
    match_result = analyze_resume_match(resume_text, application.job_description)
    tweak_suggestions = suggest_resume_tweaks(resume_text, application.job_description)

    return {
        "application": {
            "id": application.id,
            "company": application.company_name,
            "role": application.role
        },
        "job_analysis": job_analysis,
        "match": match_result,
        "suggestions": tweak_suggestions,
        "analyzed_at": datetime.utcnow().isoformat()
    }
