"""
JobKit - Pydantic schemas for request/response validation.

Defines data models for API request bodies and responses,
including validation rules and serialization configuration.
"""
from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import date, datetime
from typing import Optional, List, Literal
from enum import Enum
import re


# --- Enums for validated fields ---

class ContactType(str, Enum):
    RECRUITER = "recruiter"
    JUNIOR_DEV = "junior_dev"
    SENIOR_DEV = "senior_dev"
    HIRING_MANAGER = "hiring_manager"
    OTHER = "other"


class ConnectionStatus(str, Enum):
    NOT_CONNECTED = "not_connected"
    PENDING = "pending"
    CONNECTED = "connected"
    MESSAGED = "messaged"


class CompanySize(str, Enum):
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class ApplicationStatus(str, Enum):
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    ONSITE = "onsite"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    GHOSTED = "ghosted"


class MessageType(str, Enum):
    CONNECTION_REQUEST = "connection_request"
    INMAIL = "inmail"
    FOLLOW_UP = "follow_up"
    THANK_YOU = "thank_you"
    COLD_EMAIL = "cold_email"
    REFERRAL_REQUEST = "referral_request"
    INFORMATIONAL_INTERVIEW = "informational_interview"
    RECRUITER_REPLY = "recruiter_reply"
    APPLICATION_STATUS = "application_status"
    REJECTION_RESPONSE = "rejection_response"


class TargetType(str, Enum):
    RECRUITER = "recruiter"
    DEVELOPER = "developer"
    ALUMNI = "alumni"
    HIRING_MANAGER = "hiring_manager"
    GENERAL = "general"


# --- Helper validators ---

def validate_url(url: Optional[str]) -> Optional[str]:
    """Validate URL format if provided."""
    if url is None or url == "":
        return None
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if not url_pattern.match(url):
        raise ValueError('Invalid URL format')
    return url


def validate_linkedin_url(url: Optional[str]) -> Optional[str]:
    """Validate LinkedIn URL format if provided."""
    if url is None or url == "":
        return None
    if not url.startswith(('https://linkedin.com', 'https://www.linkedin.com', 'http://linkedin.com', 'http://www.linkedin.com')):
        raise ValueError('Must be a LinkedIn URL')
    return url


# --- Contact Schemas ---

class ContactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    email: Optional[str] = Field(None, max_length=254)
    phone_number: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, max_length=200)
    contact_type: Optional[ContactType] = None
    is_alumni: bool = False
    school_name: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=5000)

    @field_validator('linkedin_url')
    @classmethod
    def validate_linkedin(cls, v):
        return validate_linkedin_url(v)

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        if v is None or v == "":
            return None
        # Basic email validation
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(v):
            raise ValueError('Invalid email format')
        return v


class ContactCreate(ContactBase):
    connection_status: Optional[ConnectionStatus] = ConnectionStatus.NOT_CONNECTED
    next_follow_up: Optional[date] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    email: Optional[str] = Field(None, max_length=254)
    phone_number: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=200)
    role: Optional[str] = Field(None, max_length=200)
    contact_type: Optional[ContactType] = None
    is_alumni: Optional[bool] = None
    school_name: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=200)
    connection_status: Optional[ConnectionStatus] = None
    relationship_strength: Optional[int] = Field(None, ge=0, le=10)
    last_contacted: Optional[date] = None
    next_follow_up: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=5000)

    @field_validator('linkedin_url')
    @classmethod
    def validate_linkedin(cls, v):
        return validate_linkedin_url(v)


class ContactResponse(ContactBase):
    id: int
    connection_status: ConnectionStatus
    relationship_strength: int
    last_contacted: Optional[date]
    next_follow_up: Optional[date]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Company Schemas ---

class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    website: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    careers_page_url: Optional[str] = Field(None, max_length=500)
    headquarters_location: Optional[str] = Field(None, max_length=200)
    size: Optional[CompanySize] = None
    industry: Optional[str] = Field(None, max_length=100)
    tech_stack: Optional[str] = Field(None, max_length=1000)
    culture_notes: Optional[str] = Field(None, max_length=5000)
    interview_process: Optional[str] = Field(None, max_length=5000)
    priority: int = Field(0, ge=0, le=5)
    notes: Optional[str] = Field(None, max_length=5000)

    @field_validator('website')
    @classmethod
    def validate_website(cls, v):
        return validate_url(v)

    @field_validator('linkedin_url')
    @classmethod
    def validate_linkedin(cls, v):
        return validate_linkedin_url(v)

    @field_validator('careers_page_url')
    @classmethod
    def validate_careers_url(cls, v):
        return validate_url(v)


class CompanyCreate(CompanyBase):
    glassdoor_rating: Optional[float] = Field(None, ge=0, le=5)
    salary_range: Optional[str] = Field(None, max_length=100)


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    website: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    careers_page_url: Optional[str] = Field(None, max_length=500)
    headquarters_location: Optional[str] = Field(None, max_length=200)
    size: Optional[CompanySize] = None
    industry: Optional[str] = Field(None, max_length=100)
    tech_stack: Optional[str] = Field(None, max_length=1000)
    culture_notes: Optional[str] = Field(None, max_length=5000)
    interview_process: Optional[str] = Field(None, max_length=5000)
    glassdoor_rating: Optional[float] = Field(None, ge=0, le=5)
    salary_range: Optional[str] = Field(None, max_length=100)
    priority: Optional[int] = Field(None, ge=0, le=5)
    notes: Optional[str] = Field(None, max_length=5000)

    @field_validator('website', 'careers_page_url')
    @classmethod
    def validate_website(cls, v):
        return validate_url(v)


class CompanyResponse(CompanyBase):
    id: int
    glassdoor_rating: Optional[float]
    salary_range: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Application Schemas ---

class ApplicationBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    job_url: Optional[str] = Field(None, max_length=1000)
    job_description: Optional[str] = Field(None, max_length=50000)
    location: Optional[str] = Field(None, max_length=200)  # remote/hybrid/onsite + city
    source: Optional[str] = Field(None, max_length=100)  # linkedin, company_site, indeed, referral
    status: ApplicationStatus = ApplicationStatus.SAVED
    excitement_level: int = Field(3, ge=1, le=5)  # 1-5 how excited about this role
    notes: Optional[str] = Field(None, max_length=5000)

    @field_validator('job_url')
    @classmethod
    def validate_job_url(cls, v):
        return validate_url(v)


class ApplicationCreate(ApplicationBase):
    company_id: Optional[int] = None
    referral_contact_id: Optional[int] = None
    applied_date: Optional[date] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)


class ApplicationUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    role: Optional[str] = Field(None, min_length=1, max_length=200)
    job_url: Optional[str] = Field(None, max_length=1000)
    job_description: Optional[str] = Field(None, max_length=50000)
    location: Optional[str] = Field(None, max_length=200)
    source: Optional[str] = Field(None, max_length=100)
    status: Optional[ApplicationStatus] = None
    applied_date: Optional[date] = None
    response_date: Optional[date] = None
    next_step: Optional[str] = Field(None, max_length=500)
    next_step_date: Optional[date] = None
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_offered: Optional[str] = Field(None, max_length=100)
    excitement_level: Optional[int] = Field(None, ge=1, le=5)
    referral_contact_id: Optional[int] = None
    resume_version: Optional[str] = Field(None, max_length=100)
    cover_letter_used: Optional[bool] = None
    rejection_reason: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=5000)

    @field_validator('job_url')
    @classmethod
    def validate_job_url(cls, v):
        return validate_url(v)


class ApplicationResponse(ApplicationBase):
    id: int
    company_id: Optional[int]
    applied_date: Optional[date]
    response_date: Optional[date]
    next_step: Optional[str]
    next_step_date: Optional[date]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_offered: Optional[str]
    referral_contact_id: Optional[int]
    resume_version: Optional[str]
    cover_letter_used: bool
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Message Template Schemas ---

class MessageTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    message_type: MessageType
    target_type: TargetType
    subject: Optional[str] = Field(None, max_length=200)
    template: str = Field(..., min_length=1, max_length=5000)
    is_default: bool = False


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    message_type: Optional[MessageType] = None
    target_type: Optional[TargetType] = None
    subject: Optional[str] = Field(None, max_length=200)
    template: Optional[str] = Field(None, min_length=1, max_length=5000)
    is_default: Optional[bool] = None


class MessageTemplateResponse(MessageTemplateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Message Generation Schemas ---

class MessageGenerateRequest(BaseModel):
    contact_id: Optional[int] = None
    template_id: Optional[int] = None
    message_type: MessageType
    custom_context: Optional[str] = Field(None, max_length=1000)


class MessageGenerateResponse(BaseModel):
    message: str
    subject: Optional[str] = None
    contact_name: Optional[str] = None
    message_type: MessageType
    character_count: int
    ai_generated: bool = False


class AIMessageGenerateRequest(BaseModel):
    contact_id: Optional[int] = None
    message_type: MessageType
    context: Optional[str] = Field(None, max_length=1000)


class AICoverLetterRequest(BaseModel):
    job_description: str = Field(..., min_length=50)
    company_name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    tone: Optional[str] = Field("professional", pattern="^(professional|conversational|enthusiastic|formal)$")
    length: Optional[str] = Field("medium", pattern="^(short|medium|detailed)$")


class AICoverLetterResponse(BaseModel):
    cover_letter: str
    word_count: int
    character_count: int
    ai_generated: bool = False


class AISkillExtractionRequest(BaseModel):
    text: str = Field(..., min_length=20)
    context: str = Field("resume", pattern="^(resume|job)$")


class AISkillExtractionResponse(BaseModel):
    skills: List[dict]
    ai_generated: bool = False


class AIJobAnalysisResponse(BaseModel):
    analysis: dict
    ai_generated: bool = False


class AIResumeTailorRequest(BaseModel):
    job_description: str = Field(..., min_length=50)
    use_profile_resume: bool = True
    resume_text: Optional[str] = None


class AIResumeTailorResponse(BaseModel):
    analysis: dict
    ai_generated: bool = False


class AIStatusResponse(BaseModel):
    enabled: bool
    available: bool
    model: str
    models: List[str] = []


# --- Structured Resume Schemas ---

class ResumeExperience(BaseModel):
    """A single work experience entry."""
    company: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    start_date: Optional[str] = Field(None, max_length=50)  # e.g., "Jan 2020", "2020"
    end_date: Optional[str] = Field(None, max_length=50)  # None or "Present" means current
    location: Optional[str] = Field(None, max_length=200)
    bullets: List[str] = Field(default_factory=list)  # Achievement bullet points

    class Config:
        json_schema_extra = {
            "example": {
                "company": "Acme Corp",
                "title": "Senior Software Engineer",
                "start_date": "Jan 2020",
                "end_date": "Present",
                "location": "San Francisco, CA",
                "bullets": [
                    "Led development of microservices architecture serving 1M+ users",
                    "Reduced API response time by 40% through optimization"
                ]
            }
        }


class ResumeEducation(BaseModel):
    """A single education entry."""
    school: str = Field(..., min_length=1, max_length=200)
    degree: Optional[str] = Field(None, max_length=200)  # e.g., "Bachelor of Science"
    field: Optional[str] = Field(None, max_length=200)  # e.g., "Computer Science"
    year: Optional[str] = Field(None, max_length=20)  # Graduation year
    gpa: Optional[str] = Field(None, max_length=20)

    class Config:
        json_schema_extra = {
            "example": {
                "school": "MIT",
                "degree": "Bachelor of Science",
                "field": "Computer Science",
                "year": "2018",
                "gpa": "3.8"
            }
        }


class ResumeProject(BaseModel):
    """A single project entry."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Open Source CLI Tool",
                "description": "Built a CLI tool for automating deployment workflows",
                "technologies": ["Python", "Docker", "AWS"],
                "url": "https://github.com/user/project"
            }
        }


class StructuredResume(BaseModel):
    """
    Structured resume data for storage, editing, and job tailoring.
    Stored as JSON in the database.
    """
    summary: Optional[str] = Field(None, max_length=2000)
    experience: List[ResumeExperience] = Field(default_factory=list)
    education: List[ResumeEducation] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    projects: List[ResumeProject] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None  # Original text backup from parsing

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Experienced software engineer with 5+ years in full-stack development",
                "experience": [],
                "education": [],
                "skills": ["Python", "JavaScript", "React", "PostgreSQL", "AWS"],
                "projects": [],
                "certifications": ["AWS Solutions Architect"]
            }
        }


# --- User Profile Schemas ---

class UserProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone_number: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    school: Optional[str] = Field(None, max_length=200)
    graduation_year: Optional[int] = Field(None, ge=1950, le=2100)
    current_title: Optional[str] = Field(None, max_length=200)
    years_experience: Optional[int] = Field(None, ge=0, le=70)
    skills: Optional[str] = Field(None, max_length=1000)
    target_roles: Optional[str] = Field(None, max_length=500)
    preferred_locations: Optional[str] = Field(None, max_length=500)
    salary_expectations: Optional[str] = Field(None, max_length=100)
    elevator_pitch: Optional[str] = Field(None, max_length=2000)
    resume_summary: Optional[str] = Field(None, max_length=5000)
    resume_file_path: Optional[str] = Field(None, max_length=500)
    resume_data: Optional[StructuredResume] = None

    @field_validator('linkedin_url')
    @classmethod
    def validate_linkedin(cls, v):
        return validate_linkedin_url(v)


class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    phone_number: Optional[str] = Field(None, max_length=50)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=200)
    school: Optional[str] = Field(None, max_length=200)
    graduation_year: Optional[int] = Field(None, ge=1950, le=2100)
    current_title: Optional[str] = Field(None, max_length=200)
    years_experience: Optional[int] = Field(None, ge=0, le=70)
    skills: Optional[str] = Field(None, max_length=1000)
    target_roles: Optional[str] = Field(None, max_length=500)
    preferred_locations: Optional[str] = Field(None, max_length=500)
    salary_expectations: Optional[str] = Field(None, max_length=100)
    elevator_pitch: Optional[str] = Field(None, max_length=2000)
    resume_summary: Optional[str] = Field(None, max_length=5000)
    resume_file_path: Optional[str] = Field(None, max_length=500)
    resume_data: Optional[StructuredResume] = None


class UserProfileResponse(UserProfileBase):
    id: int
    updated_at: datetime
    profile_completion: Optional[int] = None  # Percentage of profile completed

    class Config:
        from_attributes = True


# --- Message History Schemas ---

class MessageHistoryCreate(BaseModel):
    contact_id: int
    template_id: Optional[int] = None
    message_type: MessageType
    message_content: str = Field(..., min_length=1, max_length=10000)


class MessageHistoryUpdate(BaseModel):
    got_response: Optional[bool] = None
    response_notes: Optional[str] = Field(None, max_length=2000)


class MessageHistoryResponse(BaseModel):
    id: int
    contact_id: int
    template_id: Optional[int]
    message_type: Optional[MessageType]
    message_content: str
    sent_at: datetime
    got_response: bool
    response_notes: Optional[str]

    class Config:
        from_attributes = True


# --- Interaction Schemas ---

class InteractionType(str, Enum):
    MESSAGE = "message"
    CALL = "call"
    COFFEE = "coffee"
    INTERVIEW = "interview"
    REFERRAL = "referral"
    OTHER = "other"


class InteractionCreate(BaseModel):
    contact_id: int
    interaction_type: InteractionType
    interaction_date: date
    notes: Optional[str] = Field(None, max_length=5000)
    follow_up_needed: bool = False
    follow_up_date: Optional[date] = None


class InteractionResponse(BaseModel):
    id: int
    contact_id: int
    interaction_type: InteractionType
    interaction_date: date
    notes: Optional[str]
    follow_up_needed: bool
    follow_up_date: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Stats/Analytics Schemas ---

class ContactStats(BaseModel):
    total: int
    by_type: dict
    by_status: dict
    needs_follow_up: int
    contacted_this_week: int
    contacted_this_month: int


class ApplicationStats(BaseModel):
    total: int
    active: int
    by_status: dict
    response_rate: float
    avg_days_to_response: Optional[float] = None
    applications_this_week: int
    applications_this_month: int


class CompanyStats(BaseModel):
    total: int
    by_size: dict
    by_priority: dict
    with_applications: int


# --- Export/Import Schemas ---

class ExportRequest(BaseModel):
    format: Literal["json", "csv"] = "json"
    include_contacts: bool = True
    include_applications: bool = True
    include_companies: bool = True
    include_messages: bool = False


class ImportResult(BaseModel):
    contacts_imported: int = 0
    applications_imported: int = 0
    companies_imported: int = 0
    errors: List[str] = []


# --- Search Schemas ---

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    search_in: List[Literal["contacts", "companies", "applications"]] = ["contacts", "companies", "applications"]
    limit: int = Field(20, ge=1, le=100)


class SearchResult(BaseModel):
    contacts: List[ContactResponse] = []
    companies: List[CompanyResponse] = []
    applications: List[ApplicationResponse] = []
