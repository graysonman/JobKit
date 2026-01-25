"""
JobKit - SQLAlchemy ORM models

Database models for contacts, companies, applications, messages, and user profile.

# =============================================================================
# TODO: Multi-User Authentication (Feature 2) - Data Isolation
# =============================================================================
# 1. Add User and OAuthAccount models:
#    class User(Base):
#        __tablename__ = "users"
#        id = Column(Integer, primary_key=True)
#        email = Column(String, unique=True, index=True, nullable=False)
#        hashed_password = Column(String, nullable=True)  # Null for OAuth-only
#        name = Column(String)
#        is_active = Column(Boolean, default=True)
#        is_verified = Column(Boolean, default=False)
#        created_at = Column(DateTime, default=datetime.utcnow)
#        oauth_accounts = relationship("OAuthAccount", back_populates="user")
#        profile = relationship("UserProfile", back_populates="user", uselist=False)
#
#    class OAuthAccount(Base):
#        __tablename__ = "oauth_accounts"
#        id = Column(Integer, primary_key=True)
#        user_id = Column(Integer, ForeignKey("users.id"))
#        provider = Column(String)  # "google", "github"
#        provider_user_id = Column(String)
#        access_token = Column(String)
#        user = relationship("User", back_populates="oauth_accounts")
#
# 2. Add user_id foreign key to ALL models:
#    - Contact: user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
#    - Company: user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
#    - Application: user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
#    - MessageTemplate: user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL = system template
#    - MessageHistory: user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
#    - UserProfile: user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
#    - Interaction: user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
#
# 3. Database migration sequence (Alembic):
#    - 001_add_users_table.py: Create users and oauth_accounts tables
#    - 002_add_user_id_columns.py: Add nullable user_id to all tables
#    - 003_migrate_existing_data.py: Create default user, assign existing data
#    - 004_make_user_id_required.py: Make user_id non-nullable, add foreign keys
# =============================================================================
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Float, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    linkedin_url = Column(String)
    email = Column(String)
    phone_number = Column(String)
    company = Column(String)
    role = Column(String)
    contact_type = Column(String)  # recruiter, junior_dev, senior_dev, hiring_manager, other
    is_alumni = Column(Boolean, default=False)
    school_name = Column(String)
    location = Column(String)  # city/region
    connection_status = Column(String, default="not_connected")
    relationship_strength = Column(Integer, default=0)
    last_contacted = Column(Date)
    next_follow_up = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship("MessageHistory", back_populates="contact")
    interactions = relationship("Interaction", back_populates="contact")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    website = Column(String)
    linkedin_url = Column(String)
    careers_page_url = Column(String)
    headquarters_location = Column(String)
    size = Column(String)
    industry = Column(String)
    tech_stack = Column(Text)
    culture_notes = Column(Text)
    interview_process = Column(Text)
    glassdoor_rating = Column(Float)
    salary_range = Column(String)
    priority = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = relationship("Application", back_populates="company")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    company_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    job_url = Column(String)
    job_description = Column(Text)
    location = Column(String)  # remote/hybrid/onsite + city
    source = Column(String)  # linkedin, company_site, indeed, referral, etc.
    status = Column(String, default="saved")
    applied_date = Column(Date)
    response_date = Column(Date)
    next_step = Column(String)
    next_step_date = Column(Date)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_offered = Column(String)
    excitement_level = Column(Integer, default=3)  # 1-5 how excited about this role
    referral_contact_id = Column(Integer, ForeignKey("contacts.id"))
    resume_version = Column(String)
    cover_letter_used = Column(Boolean, default=False)
    rejection_reason = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="applications")
    referral = relationship("Contact")


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    message_type = Column(String)  # connection_request, inmail, follow_up, thank_you, cold_email
    target_type = Column(String)   # recruiter, developer, alumni, hiring_manager, general
    subject = Column(String)
    template = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class MessageHistory(Base):
    __tablename__ = "message_history"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("message_templates.id"))
    message_type = Column(String)
    message_content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    got_response = Column(Boolean, default=False)
    response_notes = Column(Text)

    # Relationships
    contact = relationship("Contact", back_populates="messages")
    template = relationship("MessageTemplate")


class UserProfile(Base):
    """
    User profile for job search personalization.

    The resume_data column stores structured resume data as JSON:
    {
        "summary": "Professional summary text",
        "experience": [
            {"company": "", "title": "", "start_date": "", "end_date": "", "location": "", "bullets": []}
        ],
        "education": [
            {"school": "", "degree": "", "field": "", "year": "", "gpa": ""}
        ],
        "skills": ["skill1", "skill2"],
        "projects": [
            {"name": "", "description": "", "technologies": [], "url": ""}
        ],
        "certifications": ["cert1", "cert2"]
    }
    """
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    linkedin_url = Column(String)
    phone_number = Column(String)
    location = Column(String)
    school = Column(String)
    graduation_year = Column(Integer)
    current_title = Column(String)
    years_experience = Column(Integer)
    skills = Column(Text)
    target_roles = Column(Text)
    preferred_locations = Column(Text)
    salary_expectations = Column(String)
    elevator_pitch = Column(Text)
    resume_summary = Column(Text)  # Plain text backup for backward compatibility
    resume_file_path = Column(String)  # Path to uploaded resume file
    resume_data = Column(Text)  # JSON string storing structured resume sections
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    interaction_type = Column(String)  # message, call, coffee, interview, referral, other
    interaction_date = Column(Date, nullable=False)
    notes = Column(Text)
    follow_up_needed = Column(Boolean, default=False)
    follow_up_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    contact = relationship("Contact", back_populates="interactions")
