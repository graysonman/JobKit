"""
JobKit - Resume and cover letter API endpoints.

Endpoints for analyzing job descriptions, matching resumes to jobs,
generating cover letters, parsing resumes, and suggesting improvements.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import re
import os
import tempfile
import json
import logging

from ..database import get_db
from ..models import UserProfile, Application
from ..schemas import StructuredResume, ResumeExperience, ResumeEducation, ResumeProject
from ..services.resume_helper import (
    extract_keywords_from_job,
    analyze_resume_match,
    generate_cover_letter,
    suggest_resume_tweaks,
    parse_resume_text,
    parse_resume_file,
    tailor_resume_for_job
)
from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..query_helpers import get_owned_or_404
from ..services.ai_service import ai_service, AIServiceError
from ..schemas import (
    AICoverLetterRequest, AICoverLetterResponse,
    AISkillExtractionRequest, AISkillExtractionResponse,
    AIJobAnalysisResponse, AIResumeTailorRequest, AIResumeTailorResponse
)

router = APIRouter()
logger = logging.getLogger("jobkit.resume")


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
    tone: Optional[str] = "professional"
    length: Optional[str] = "medium"


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


class ParseResumeTextRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)


class ResumeUploadResponse(BaseModel):
    message: str
    resume: StructuredResume
    saved_to_profile: bool = False


class TailorResumeRequest(BaseModel):
    job_description: str = Field(..., min_length=50)
    use_profile_resume: bool = True
    resume_text: Optional[str] = None


class TailorSuggestion(BaseModel):
    section: str
    original: Optional[str] = None
    suggestion: str
    priority: str
    reason: str


class TailorResumeResponse(BaseModel):
    match_score: float
    keywords_to_add: List[str]
    skills_to_emphasize: List[str]
    skills_to_add: List[str]
    suggestions: List[TailorSuggestion]


class ProfileResumeUpdateRequest(BaseModel):
    """Request to update specific sections of the profile resume."""
    summary: Optional[str] = None
    experience: Optional[List[ResumeExperience]] = None
    education: Optional[List[ResumeEducation]] = None
    skills: Optional[List[str]] = None
    projects: Optional[List[ResumeProject]] = None
    certifications: Optional[List[str]] = None


# --- Resume Upload & Parsing Endpoints ---

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _serialize_resume_data(resume_data: StructuredResume) -> str:
    if resume_data is None:
        return None
    return json.dumps(resume_data.model_dump())


def _deserialize_resume_data(json_str: str) -> Optional[StructuredResume]:
    if json_str is None:
        return None
    try:
        data = json.loads(json_str)
        return StructuredResume(**data)
    except (json.JSONDecodeError, Exception):
        return None


def _get_user_profile(db: Session, user: User):
    return db.query(UserProfile).filter(UserProfile.user_id == user.id).first()


@router.post("/upload-resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    save_to_profile: bool = Query(False, description="Save parsed resume to user profile"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and parse a resume file.

    Supports PDF, DOCX, and TXT files. Optionally saves to user profile.
    """
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    try:
        if ext == '.txt':
            text = content.decode('utf-8')
            resume = parse_resume_text(text)
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                resume = parse_resume_file(tmp_path)
            finally:
                os.unlink(tmp_path)

    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {str(e)}")

    saved = False
    if save_to_profile:
        profile = _get_user_profile(db, current_user)
        if profile:
            profile.resume_data = _serialize_resume_data(resume)
            if resume.summary:
                profile.resume_summary = resume.summary
            if resume.skills:
                profile.skills = ', '.join(resume.skills)
            db.commit()
            saved = True
        else:
            new_profile = UserProfile(
                user_id=current_user.id,
                name="",
                resume_data=_serialize_resume_data(resume),
                resume_summary=resume.summary,
                skills=', '.join(resume.skills) if resume.skills else None
            )
            db.add(new_profile)
            db.commit()
            saved = True

    return ResumeUploadResponse(
        message="Resume parsed successfully",
        resume=resume,
        saved_to_profile=saved
    )


@router.post("/parse-resume-text", response_model=StructuredResume)
def parse_resume_text_endpoint(request: ParseResumeTextRequest):
    """Parse raw resume text into structured sections."""
    try:
        resume = parse_resume_text(request.resume_text)
        return resume
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume text: {str(e)}")


@router.get("/profile-resume", response_model=StructuredResume)
def get_profile_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the user's stored structured resume from their profile."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create a profile first.")

    resume = _deserialize_resume_data(profile.resume_data)
    if not resume:
        return StructuredResume(
            summary=profile.resume_summary,
            skills=profile.skills.split(', ') if profile.skills else []
        )

    return resume


@router.put("/profile-resume", response_model=StructuredResume)
def update_profile_resume(
    request: ProfileResumeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update specific sections of the user's stored resume."""
    profile = _get_user_profile(db, current_user)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please create a profile first.")

    resume = _deserialize_resume_data(profile.resume_data)
    if not resume:
        resume = StructuredResume()

    update_data = request.model_dump(exclude_unset=True)

    if 'summary' in update_data:
        resume.summary = update_data['summary']
    if 'experience' in update_data:
        resume.experience = update_data['experience']
    if 'education' in update_data:
        resume.education = update_data['education']
    if 'skills' in update_data:
        resume.skills = update_data['skills']
    if 'projects' in update_data:
        resume.projects = update_data['projects']
    if 'certifications' in update_data:
        resume.certifications = update_data['certifications']

    profile.resume_data = _serialize_resume_data(resume)

    if resume.summary:
        profile.resume_summary = resume.summary
    if resume.skills:
        profile.skills = ', '.join(resume.skills)

    db.commit()
    db.refresh(profile)

    return resume


@router.post("/tailor-resume", response_model=TailorResumeResponse)
def tailor_resume_endpoint(
    request: TailorResumeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get tailored suggestions for a resume based on a job description."""
    if request.use_profile_resume:
        profile = _get_user_profile(db, current_user)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found. Please create a profile first.")

        resume = _deserialize_resume_data(profile.resume_data)
        if not resume:
            if profile.resume_summary or profile.skills:
                resume = StructuredResume(
                    summary=profile.resume_summary,
                    skills=profile.skills.split(', ') if profile.skills else []
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="No resume data in profile. Upload a resume or provide resume_text."
                )
    else:
        if not request.resume_text:
            raise HTTPException(
                status_code=400,
                detail="resume_text is required when use_profile_resume is false"
            )
        resume = parse_resume_text(request.resume_text)

    result = tailor_resume_for_job(resume, request.job_description)

    suggestions = [
        TailorSuggestion(
            section=s.section,
            original=s.original,
            suggestion=s.suggestion,
            priority=s.priority,
            reason=s.reason
        )
        for s in result.suggestions
    ]

    return TailorResumeResponse(
        match_score=result.match_score,
        keywords_to_add=result.keywords_to_add,
        skills_to_emphasize=result.skills_to_emphasize,
        skills_to_add=result.skills_to_add,
        suggestions=suggestions
    )


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a cover letter based on user profile and job description."""
    profile = _get_user_profile(db, current_user)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a cover letter for a specific application."""
    application = get_owned_or_404(db, Application, application_id, current_user, "Application")

    if not application.job_description:
        raise HTTPException(status_code=400, detail="Application has no job description")

    profile = _get_user_profile(db, current_user)
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


# --- AI-Powered Endpoints ---

@router.post("/generate-cover-letter-ai", response_model=AICoverLetterResponse)
async def generate_cover_letter_ai_endpoint(
    request: AICoverLetterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a cover letter using AI (Ollama).

    Falls back to template-based generation if AI is unavailable.
    """
    profile = _get_user_profile(db, current_user)
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

    # Load resume text for AI context
    resume_text = ""
    resume_data = _deserialize_resume_data(profile.resume_data)
    if resume_data and resume_data.raw_text:
        resume_text = resume_data.raw_text
    elif profile.resume_summary:
        resume_text = profile.resume_summary

    # Try AI generation
    try:
        if await ai_service.is_available():
            cover_letter, ai_generated = await ai_service.generate_cover_letter_ai(
                profile=user_profile,
                job_description=request.job_description,
                company_name=request.company_name,
                role=request.role,
                tone=request.tone or "professional",
                length=request.length or "medium",
                resume_text=resume_text
            )
            return AICoverLetterResponse(
                cover_letter=cover_letter,
                word_count=len(cover_letter.split()),
                character_count=len(cover_letter),
                ai_generated=True
            )
    except Exception as e:
        logger.warning(f"AI cover letter generation failed, falling back to template: {e}")
        pass  # Fall through to template-based generation

    # Fallback: template-based generation
    cover_letter = generate_cover_letter(
        user_profile=user_profile,
        job_description=request.job_description,
        company_name=request.company_name,
        role=request.role,
        tone=request.tone or "professional",
        length=request.length or "medium"
    )

    return AICoverLetterResponse(
        cover_letter=cover_letter,
        word_count=len(cover_letter.split()),
        character_count=len(cover_letter),
        ai_generated=False
    )


@router.post("/extract-skills-ai", response_model=AISkillExtractionResponse)
async def extract_skills_ai_endpoint(request: AISkillExtractionRequest):
    """
    Semantically extract and categorize skills from text using AI.

    Falls back to keyword-based extraction if AI is unavailable.
    """
    # Try AI extraction
    try:
        if await ai_service.is_available():
            skills = await ai_service.extract_skills_semantic(
                text=request.text,
                context=request.context
            )
            if skills:
                return AISkillExtractionResponse(skills=skills, ai_generated=True)
    except Exception as e:
        logger.warning(f"AI skill extraction failed, falling back to keyword-based: {e}")
        pass

    # Fallback: keyword-based extraction
    if request.context == "job":
        analysis = extract_keywords_from_job(request.text)
        skills = [
            {"skill": s, "category": "required", "confidence": 0.9}
            for s in analysis.get("required_skills", [])
        ] + [
            {"skill": s, "category": "preferred", "confidence": 0.7}
            for s in analysis.get("preferred_skills", [])
        ]
    else:
        # Parse resume text and extract skills
        resume = parse_resume_text(request.text)
        skills = [
            {"skill": s, "category": "detected", "confidence": 0.8}
            for s in resume.skills
        ]

    return AISkillExtractionResponse(skills=skills, ai_generated=False)


@router.post("/analyze-job-ai", response_model=AIJobAnalysisResponse)
async def analyze_job_ai_endpoint(request: JobAnalysisRequest):
    """
    Analyze a job description using AI for deeper insights.

    Falls back to keyword-based analysis if AI is unavailable.
    """
    # Try AI analysis
    try:
        if await ai_service.is_available():
            analysis = await ai_service.analyze_job_description(request.job_description)
            if analysis:
                return AIJobAnalysisResponse(analysis=analysis, ai_generated=True)
    except Exception as e:
        logger.warning(f"AI job analysis failed, falling back to keyword-based: {e}")
        pass

    # Fallback: keyword-based analysis
    analysis = extract_keywords_from_job(request.job_description)
    return AIJobAnalysisResponse(analysis=analysis, ai_generated=False)


@router.post("/tailor-resume-ai", response_model=AIResumeTailorResponse)
async def tailor_resume_ai_endpoint(
    request: AIResumeTailorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get AI-powered suggestions for tailoring a resume to a job.

    Falls back to keyword-based tailoring if AI is unavailable.
    """
    # Get resume text
    resume_text = request.resume_text
    if request.use_profile_resume:
        profile = _get_user_profile(db, current_user)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        resume_data = _deserialize_resume_data(profile.resume_data)
        if resume_data and resume_data.raw_text:
            resume_text = resume_data.raw_text
        elif profile.resume_summary:
            resume_text = profile.resume_summary
        elif not resume_text:
            raise HTTPException(
                status_code=400,
                detail="No resume data in profile. Upload a resume or provide resume_text."
            )

    if not resume_text:
        raise HTTPException(status_code=400, detail="resume_text is required when use_profile_resume is false")

    # Try AI tailoring
    try:
        if await ai_service.is_available():
            analysis = await ai_service.tailor_resume_suggestions(
                resume_text=resume_text,
                job_description=request.job_description
            )
            if analysis:
                return AIResumeTailorResponse(analysis=analysis, ai_generated=True)
    except Exception as e:
        logger.warning(f"AI resume tailoring failed, falling back to keyword-based: {e}")
        pass

    # Fallback: keyword-based tailoring
    resume = parse_resume_text(resume_text)
    result = tailor_resume_for_job(resume, request.job_description)
    analysis = {
        "match_score": result.match_score,
        "keywords_to_add": result.keywords_to_add,
        "skills_to_emphasize": result.skills_to_emphasize,
        "skills_to_add": result.skills_to_add,
        "suggestions": [
            {
                "section": s.section,
                "original": s.original,
                "suggestion": s.suggestion,
                "priority": s.priority,
                "reason": s.reason
            }
            for s in result.suggestions
        ]
    }
    return AIResumeTailorResponse(analysis=analysis, ai_generated=False)


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

    if not re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text):
        issues.append("No email address detected")
        score -= 10

    if not re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text):
        issues.append("No phone number detected")
        score -= 5

    common_sections = ['experience', 'education', 'skills', 'summary', 'objective', 'work history']
    found_sections = sum(1 for s in common_sections if s.lower() in resume_text.lower())
    if found_sections < 2:
        issues.append("Missing standard section headings (Experience, Education, Skills)")
        recommendations.append("Add clear section headings like 'Experience', 'Education', 'Skills'")
        score -= 15

    word_count = len(resume_text.split())
    if word_count < 200:
        issues.append(f"Resume seems too short ({word_count} words)")
        recommendations.append("Add more detail to your experience and skills sections")
        score -= 10
    elif word_count > 1500:
        format_warnings.append(f"Resume may be too long ({word_count} words) - consider condensing")
        score -= 5

    if re.search(r'[^\x00-\x7F]+', resume_text):
        format_warnings.append("Contains special characters that may not parse correctly")
        score -= 5

    if '|' in resume_text or '\t\t' in resume_text:
        format_warnings.append("May contain tables or columns - ATS often struggles with these")
        recommendations.append("Use a single-column format for better ATS parsing")
        score -= 10

    action_verbs = ['managed', 'developed', 'created', 'led', 'implemented', 'designed',
                   'achieved', 'improved', 'built', 'launched', 'increased', 'reduced']
    found_verbs = sum(1 for v in action_verbs if v.lower() in resume_text.lower())
    if found_verbs < 3:
        recommendations.append("Use more action verbs (managed, developed, achieved, etc.)")
        score -= 5

    if not re.search(r'\d+%|\$\d+|\d+ years?|\d+ projects?|\d+ team', resume_text.lower()):
        recommendations.append("Add quantifiable achievements (percentages, dollar amounts, numbers)")
        score -= 5

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

    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
                 'our', 'your', 'their', 'this', 'that', 'these', 'those', 'it',
                 'we', 'you', 'they', 'he', 'she', 'who', 'which', 'what', 'where',
                 'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
                 'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same',
                 'than', 'too', 'very', 'just', 'also', 'work', 'ability', 'experience'}

    job_words = re.findall(r'\b[a-z]+\b', job_lower)
    job_keywords = [w for w in job_words if w not in stop_words and len(w) > 2]

    keyword_freq = {}
    for word in job_keywords:
        keyword_freq[word] = keyword_freq.get(word, 0) + 1

    top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    job_keywords_list = [k for k, v in top_keywords]

    found = []
    missing = []
    for keyword in job_keywords_list:
        if keyword in resume_lower:
            found.append(keyword)
        else:
            missing.append(keyword)

    density_score = len(found) / len(job_keywords_list) * 100 if job_keywords_list else 0

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Comprehensive resume analysis for a specific job application."""
    application = get_owned_or_404(db, Application, application_id, current_user, "Application")

    if not application.job_description:
        raise HTTPException(status_code=400, detail="Application has no job description")

    if not resume_text:
        profile = _get_user_profile(db, current_user)
        if not profile or not profile.resume_summary:
            raise HTTPException(status_code=400, detail="No resume text provided and no resume summary in profile")
        resume_text = profile.resume_summary

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
