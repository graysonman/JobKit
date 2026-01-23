-- =============================================================================
-- JOB SEARCH TOOLKIT DATABASE SCHEMA
-- =============================================================================
-- This file serves as the reference for all database tables and relationships.
-- The actual database is created via SQLAlchemy models in app/models.py
-- =============================================================================

-- -----------------------------------------------------------------------------
-- CONTACTS TABLE
-- Stores networking contacts (recruiters, developers, hiring managers, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    linkedin_url TEXT,
    email TEXT,
    company TEXT,
    role TEXT,
    contact_type TEXT CHECK(contact_type IN ('recruiter', 'junior_dev', 'senior_dev', 'hiring_manager', 'other')),
    is_alumni BOOLEAN DEFAULT 0,
    school_name TEXT,                    -- Which school (if alumni)
    connection_status TEXT DEFAULT 'not_connected' CHECK(connection_status IN ('not_connected', 'pending', 'connected', 'messaged')),
    relationship_strength INTEGER DEFAULT 0 CHECK(relationship_strength BETWEEN 0 AND 5),  -- 0=cold, 5=strong
    last_contacted DATE,
    next_follow_up DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for common queries
CREATE INDEX idx_contacts_company ON contacts(company);
CREATE INDEX idx_contacts_type ON contacts(contact_type);
CREATE INDEX idx_contacts_alumni ON contacts(is_alumni);
CREATE INDEX idx_contacts_follow_up ON contacts(next_follow_up);

-- -----------------------------------------------------------------------------
-- COMPANIES TABLE
-- Stores research notes about target companies
-- -----------------------------------------------------------------------------
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    website TEXT,
    linkedin_url TEXT,
    size TEXT CHECK(size IN ('startup', 'small', 'medium', 'large', 'enterprise')),
    industry TEXT,
    tech_stack TEXT,                     -- Comma-separated or JSON
    culture_notes TEXT,
    interview_process TEXT,              -- Notes on their interview process
    glassdoor_rating REAL,
    salary_range TEXT,                   -- General salary info if known
    priority INTEGER DEFAULT 0 CHECK(priority BETWEEN 0 AND 5),  -- How much you want to work there
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_companies_priority ON companies(priority);

-- -----------------------------------------------------------------------------
-- APPLICATIONS TABLE
-- Tracks job applications and their status through the pipeline
-- -----------------------------------------------------------------------------
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    company_name TEXT NOT NULL,          -- Denormalized for quick access
    role TEXT NOT NULL,
    job_url TEXT,
    job_description TEXT,                -- Store the JD for resume matching
    status TEXT DEFAULT 'saved' CHECK(status IN (
        'saved',           -- Saved to apply later
        'applied',         -- Application submitted
        'phone_screen',    -- Phone/recruiter screen scheduled/completed
        'technical',       -- Technical interview stage
        'onsite',          -- Onsite/final round
        'offer',           -- Received offer
        'accepted',        -- Accepted offer
        'rejected',        -- Rejected at any stage
        'withdrawn',       -- You withdrew
        'ghosted'          -- No response after reasonable time
    )),
    applied_date DATE,
    response_date DATE,                  -- When they responded
    next_step TEXT,                      -- What's the next action
    next_step_date DATE,                 -- When is it
    salary_offered TEXT,
    referral_contact_id INTEGER REFERENCES contacts(id),  -- Who referred you
    resume_version TEXT,                 -- Which resume version used
    cover_letter_used BOOLEAN DEFAULT 0,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_company ON applications(company_id);
CREATE INDEX idx_applications_next_step ON applications(next_step_date);

-- -----------------------------------------------------------------------------
-- MESSAGE_TEMPLATES TABLE
-- Stores reusable message templates for outreach
-- -----------------------------------------------------------------------------
CREATE TABLE message_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    message_type TEXT CHECK(message_type IN ('connection_request', 'inmail', 'follow_up', 'thank_you', 'cold_email')),
    target_type TEXT CHECK(target_type IN ('recruiter', 'developer', 'alumni', 'hiring_manager', 'general')),
    subject TEXT,                        -- For emails/InMails
    template TEXT NOT NULL,              -- Message body with {placeholders}
    -- Available placeholders: {name}, {company}, {role}, {school}, {my_name}, {my_background}
    is_default BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- MESSAGE_HISTORY TABLE
-- Tracks messages sent to contacts
-- -----------------------------------------------------------------------------
CREATE TABLE message_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    template_id INTEGER REFERENCES message_templates(id),
    message_type TEXT,
    message_content TEXT NOT NULL,       -- The actual sent message
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    got_response BOOLEAN DEFAULT 0,
    response_notes TEXT
);

CREATE INDEX idx_message_history_contact ON message_history(contact_id);

-- -----------------------------------------------------------------------------
-- USER_PROFILE TABLE
-- Stores your information for message personalization
-- -----------------------------------------------------------------------------
CREATE TABLE user_profile (
    id INTEGER PRIMARY KEY CHECK(id = 1),  -- Only one row allowed
    name TEXT NOT NULL,
    email TEXT,
    linkedin_url TEXT,
    school TEXT,                         -- For alumni matching
    graduation_year INTEGER,
    current_title TEXT,
    years_experience INTEGER,
    skills TEXT,                         -- Comma-separated key skills
    target_roles TEXT,                   -- What roles you're looking for
    elevator_pitch TEXT,                 -- 30-second intro
    resume_summary TEXT,                 -- Key resume points for cover letters
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- INTERACTIONS TABLE
-- Log of all interactions with contacts (calls, coffees, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    interaction_type TEXT CHECK(interaction_type IN ('message', 'call', 'coffee', 'interview', 'referral', 'other')),
    interaction_date DATE NOT NULL,
    notes TEXT,
    follow_up_needed BOOLEAN DEFAULT 0,
    follow_up_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_interactions_contact ON interactions(contact_id);
CREATE INDEX idx_interactions_follow_up ON interactions(follow_up_date);

-- -----------------------------------------------------------------------------
-- RELATIONSHIPS
-- -----------------------------------------------------------------------------
-- contacts.company -> can link to companies.name (soft reference)
-- applications.company_id -> companies.id (foreign key)
-- applications.referral_contact_id -> contacts.id (foreign key)
-- message_history.contact_id -> contacts.id (foreign key)
-- message_history.template_id -> message_templates.id (foreign key)
-- interactions.contact_id -> contacts.id (foreign key)
