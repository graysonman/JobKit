"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, HttpUrl
from datetime import date, datetime
from typing import Optional, List

# --- Contact Schemas ---
class ContactBase(BaseModel):
    name: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    contact_type: Optional[str] = None
    is_alumni: bool = False
    school_name: Optional[str] = None
    notes: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    contact_type: Optional[str] = None
    is_alumni: Optional[bool] = None
    school_name: Optional[str] = None
    connection_status: Optional[str] = None
    relationship_strength: Optional[int] = None
    last_contacted: Optional[date] = None
    next_follow_up: Optional[date] = None
    notes: Optional[str] = None

class ContactResponse(ContactBase):
    id: int
    connection_status: str
    relationship_strength: int
    last_contacted: Optional[date]
    next_follow_up: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Company Schemas ---
class CompanyBase(BaseModel):
    name: str
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    tech_stack: Optional[str] = None
    culture_notes: Optional[str] = None
    interview_process: Optional[str] = None
    priority: int = 0
    notes: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    # All fields optional for partial updates
    name: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    tech_stack: Optional[str] = None
    culture_notes: Optional[str] = None
    interview_process: Optional[str] = None
    glassdoor_rating: Optional[float] = None
    salary_range: Optional[str] = None
    priority: Optional[int] = None
    notes: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: int
    glassdoor_rating: Optional[float]
    salary_range: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Application Schemas ---
class ApplicationBase(BaseModel):
    company_name: str
    role: str
    job_url: Optional[str] = None
    job_description: Optional[str] = None
    status: str = "saved"
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    company_id: Optional[int] = None
    referral_contact_id: Optional[int] = None

class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = None
    role: Optional[str] = None
    job_url: Optional[str] = None
    job_description: Optional[str] = None
    status: Optional[str] = None
    applied_date: Optional[date] = None
    response_date: Optional[date] = None
    next_step: Optional[str] = None
    next_step_date: Optional[date] = None
    salary_offered: Optional[str] = None
    referral_contact_id: Optional[int] = None
    resume_version: Optional[str] = None
    cover_letter_used: Optional[bool] = None
    notes: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: int
    company_id: Optional[int]
    applied_date: Optional[date]
    response_date: Optional[date]
    next_step: Optional[str]
    next_step_date: Optional[date]
    salary_offered: Optional[str]
    referral_contact_id: Optional[int]
    resume_version: Optional[str]
    cover_letter_used: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Message Template Schemas ---
class MessageTemplateBase(BaseModel):
    name: str
    message_type: str
    target_type: str
    subject: Optional[str] = None
    template: str
    is_default: bool = False

class MessageTemplateCreate(MessageTemplateBase):
    pass

class MessageTemplateResponse(MessageTemplateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Message Generation Schemas ---
class MessageGenerateRequest(BaseModel):
    contact_id: int
    template_id: Optional[int] = None
    message_type: str  # connection_request, inmail, follow_up
    # TODO Phase 3: Add custom_context field for additional personalization

class MessageGenerateResponse(BaseModel):
    message: str
    subject: Optional[str] = None
    contact_name: str
    message_type: str
    # TODO Phase 3: Add suggested_alternatives list


# --- User Profile Schemas ---
class UserProfileBase(BaseModel):
    name: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    school: Optional[str] = None
    graduation_year: Optional[int] = None
    current_title: Optional[str] = None
    years_experience: Optional[int] = None
    skills: Optional[str] = None
    target_roles: Optional[str] = None
    elevator_pitch: Optional[str] = None
    resume_summary: Optional[str] = None

class UserProfileUpdate(UserProfileBase):
    name: Optional[str] = None

class UserProfileResponse(UserProfileBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Message History Schemas ---
class MessageHistoryCreate(BaseModel):
    contact_id: int
    template_id: Optional[int] = None
    message_type: str
    message_content: str

class MessageHistoryResponse(BaseModel):
    id: int
    contact_id: int
    template_id: Optional[int]
    message_type: Optional[str]
    message_content: str
    sent_at: datetime
    got_response: bool
    response_notes: Optional[str]

    class Config:
        from_attributes = True


# TODO Phase 5: Add ResumeAnalysis schemas
# class JobDescriptionAnalysis(BaseModel):
#     required_skills: List[str]
#     preferred_skills: List[str]
#     experience_level: str
#     key_responsibilities: List[str]
#     matching_score: float
#     missing_keywords: List[str]
#     suggestions: List[str]

# TODO Phase 5: Add CoverLetter schemas
# class CoverLetterRequest(BaseModel):
#     job_description: str
#     company_name: str
#     role: str
#     custom_points: Optional[List[str]] = None

# class CoverLetterResponse(BaseModel):
#     cover_letter: str
#     key_points_addressed: List[str]
