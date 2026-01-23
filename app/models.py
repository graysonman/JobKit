"""
JobKit - SQLAlchemy ORM models

Database models for contacts, companies, applications, messages, and user profile.
"""
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Float, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

# TODO: Add Tag model for tagging contacts/companies/applications
# TODO: Add Reminder model for scheduled follow-up notifications
# TODO: Add ResumeVersion model to store different resume versions
# TODO: Add InterviewNote model to track interview feedback per application

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    linkedin_url = Column(String)
    email = Column(String)
    company = Column(String)
    role = Column(String)
    contact_type = Column(String)  # recruiter, junior_dev, senior_dev, hiring_manager, other
    is_alumni = Column(Boolean, default=False)
    school_name = Column(String)
    connection_status = Column(String, default="not_connected")
    relationship_strength = Column(Integer, default=0)
    last_contacted = Column(Date)
    next_follow_up = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # TODO: Add phone_number field
    # TODO: Add profile_photo_url field (for LinkedIn profile pic caching)
    # TODO: Add company_id foreign key to link to Company model
    # TODO: Add location field (city/region)
    # TODO: Add tags relationship for custom categorization
    # TODO: Add response_rate computed field (messages sent vs responses received)

    # Relationships
    messages = relationship("MessageHistory", back_populates="contact")
    interactions = relationship("Interaction", back_populates="contact")
    # TODO: Add referrals relationship to applications


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    website = Column(String)
    linkedin_url = Column(String)
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

    # TODO: Add logo_url field (fetch from Clearbit or similar API)
    # TODO: Add headquarters_location field
    # TODO: Add careers_page_url field
    # TODO: Add levels_fyi_url field for salary data
    # TODO: Add blind_rating field (teamblind.com)
    # TODO: Add funding_stage field (for startups: seed, series A, etc.)
    # TODO: Add employee_count field (more specific than size category)
    # TODO: Add contacts relationship to show contacts at this company

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
    status = Column(String, default="saved")
    applied_date = Column(Date)
    response_date = Column(Date)
    next_step = Column(String)
    next_step_date = Column(Date)
    salary_offered = Column(String)
    referral_contact_id = Column(Integer, ForeignKey("contacts.id"))
    resume_version = Column(String)
    cover_letter_used = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # TODO: Add location field (remote/hybrid/onsite + city)
    # TODO: Add salary_min and salary_max fields (numeric) for filtering
    # TODO: Add source field (LinkedIn, company site, Indeed, referral, etc.)
    # TODO: Add excitement_level field (1-5 how excited about this role)
    # TODO: Add rejection_reason field (for learning from rejections)
    # TODO: Add cover_letter_text field to store the actual cover letter used
    # TODO: Add interview_notes relationship for per-round interview tracking
    # TODO: Add timeline/status_history relationship to track status changes over time

    # Relationships
    company = relationship("Company", back_populates="applications")
    referral = relationship("Contact")
    # TODO: Add relationship to resume versions


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    message_type = Column(String)  # connection_request, inmail, follow_up, thank_you, cold_email
    target_type = Column(String)   # recruiter, developer, alumni, hiring_manager, general
    subject = Column(String)
    template = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # TODO Phase 3: Add usage count tracking
    # TODO Phase 3: Add effectiveness rating based on responses


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
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    linkedin_url = Column(String)
    school = Column(String)
    graduation_year = Column(Integer)
    current_title = Column(String)
    years_experience = Column(Integer)
    skills = Column(Text)
    target_roles = Column(Text)
    elevator_pitch = Column(Text)
    resume_summary = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # TODO Phase 5: Add resume_file_path for stored resume
    # TODO Phase 5: Add multiple target role support with priorities


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
