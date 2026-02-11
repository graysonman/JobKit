"""
JobKit - AI Prompt Templates

Prompt templates for various AI-powered features.

These prompts are designed for instruction-tuned models like:
- Llama 3.3 70B (Groq)
- Mixtral 8x7B (Groq)
- Gemma 2 9B (Groq)
"""

# -----------------------------------------------------------------------------
# Cover Letter Generation Prompt
# -----------------------------------------------------------------------------
COVER_LETTER_PROMPT = """You are a professional resume writer helping job seekers create compelling cover letters.

**Candidate Information:**
- Name: {name}
- Current Title: {current_title}
- Key Skills: {skills}
- Years of Experience: {years_experience}
- About Me: {elevator_pitch}

**Candidate Resume:**
{resume_text}

**Target Position:**
- Company: {company_name}
- Role: {role}

**Job Description:**
{job_description}

**Instructions:**
Draw from the candidate's actual resume experience, projects, and achievements to write a {length} cover letter in a {tone} tone that:
1. Opens with a compelling hook that shows genuine interest in {company_name}
2. Highlights 2-3 relevant skills/experiences that match the job requirements
3. Demonstrates understanding of the company and role
4. Ends with a confident call-to-action

Length guidelines:
- short: ~150 words (3 concise paragraphs)
- medium: ~250 words (4 paragraphs)
- detailed: ~350 words (5 paragraphs with specific examples)

Tone guidelines:
- professional: Formal but warm, focuses on qualifications
- conversational: Friendly and approachable, still professional
- enthusiastic: High energy, shows genuine excitement
- formal: Traditional business letter format

Write only the cover letter content (no meta-commentary). Start with "Dear Hiring Manager," and end with the candidate's name.

Cover Letter:"""


# -----------------------------------------------------------------------------
# Skill Extraction Prompt
# -----------------------------------------------------------------------------
SKILL_EXTRACTION_PROMPT = """You are an expert at analyzing {context}s to extract technical and professional skills.

**Text to Analyze:**
{text}

**Instructions:**
Extract all skills mentioned in the text and categorize them. Return a JSON array with the following structure:

[
  {{"skill": "skill name", "category": "category", "confidence": 0.0-1.0}},
  ...
]

Categories:
- languages: Programming languages (Python, JavaScript, etc.)
- frontend: Frontend frameworks and tools (React, Vue, CSS, etc.)
- backend: Backend frameworks and tools (Node.js, Django, etc.)
- databases: Database technologies (PostgreSQL, MongoDB, etc.)
- cloud: Cloud platforms and services (AWS, Azure, GCP, etc.)
- devops: DevOps and infrastructure tools (Docker, Kubernetes, CI/CD, etc.)
- data_science: ML, AI, data analysis tools (TensorFlow, Pandas, etc.)
- mobile: Mobile development (iOS, Android, React Native, etc.)
- testing: Testing frameworks and methodologies
- security: Security tools and practices
- tools: General development tools (Git, IDEs, etc.)
- soft_skills: Non-technical skills (Leadership, Communication, etc.)

Only include skills that are clearly mentioned or strongly implied. Confidence should reflect how explicitly the skill is mentioned.

JSON Response:"""


# -----------------------------------------------------------------------------
# Message Generation Prompt
# -----------------------------------------------------------------------------
MESSAGE_GENERATION_PROMPT = """You are an expert networking coach helping job seekers craft personalized outreach messages.

**Sender (You):**
- Name: {my_name}
- Current Title: {my_title}
- Key Skills: {my_skills}
- About: {elevator_pitch}

**Your Background (use to personalize the message):**
{resume_summary}

**Recipient:**
- Name: {contact_name}
- Company: {contact_company}
- Role: {contact_role}
- Contact Type: {contact_type}
- Alumni Connection: {is_alumni}
- Shared School: {school}

**Message Type:** {message_type}
**Additional Context:** {context}

**Message Type Guidelines:**

connection_request (LinkedIn - max 300 characters):
- Be concise and specific about why you want to connect
- Mention a common connection point (alumni, shared interest, their work)
- No hard ask - just express interest in connecting

inmail (LinkedIn InMail - max 1900 characters):
- Open with something specific about their work/company
- Brief introduction of yourself and relevance
- Clear but soft ask (coffee chat, quick call, advice)
- Professional but personable tone

follow_up:
- Reference previous interaction if any
- Keep it brief and value-focused
- Clear next step

thank_you:
- Express genuine gratitude
- Reference specific points from conversation
- Reiterate interest without being pushy

cold_email:
- Compelling subject line suggestion
- Why you're reaching out to them specifically
- Brief relevant background
- Clear, low-commitment ask

referral_request (asking contact to refer you for a role at their company - max 500 chars):
- Mention the specific role you're interested in
- Briefly explain why you're a good fit
- Make it easy for them (offer to send resume, job link, etc.)
- Be appreciative but not desperate
- Acknowledge it's okay if they can't help

informational_interview (requesting a brief chat to learn about their role/company - max 400 chars):
- Express genuine curiosity about their career path or company
- Be specific about what you want to learn (not just "pick your brain")
- Suggest a short time commitment (15-20 minutes)
- Offer flexibility on timing
- No job ask - this is purely informational

recruiter_reply (responding to a recruiter who reached out to you - max 600 chars):
- Thank them for reaching out
- Express interest (or politely decline if not interested)
- Ask clarifying questions about the role if interested
- Mention relevant experience briefly
- Be professional but enthusiastic

application_status (following up on your application status - max 300 chars):
- Reference the specific role and when you applied
- Express continued interest
- Keep it brief and professional
- Don't sound desperate or demanding
- One gentle ask for an update

rejection_response (graciously responding to a rejection - max 300 chars):
- Thank them for considering you and letting you know
- Express continued interest in future opportunities
- Keep it brief and gracious
- Leave the door open professionally
- No begging or asking for reconsideration

**Instructions:**
Write a personalized {message_type} message. Be genuine, avoid cliches like "I hope this finds you well" or "pick your brain". Show you've done your research. Match the appropriate length for the message type.

Message:"""


# -----------------------------------------------------------------------------
# Job Description Analysis Prompt
# -----------------------------------------------------------------------------
JOB_ANALYSIS_PROMPT = """You are an expert career advisor analyzing job postings.

**Job Description:**
{job_description}

**Instructions:**
Analyze this job posting and extract the following information in JSON format:

{{
  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill1", "skill2", ...],
  "experience_level": "entry-level|mid-level|senior|lead|executive",
  "years_required": number or null,
  "education_requirements": ["requirement1", ...],
  "key_responsibilities": ["responsibility1", ...],
  "company_culture_signals": ["signal1", ...],
  "red_flags": ["flag1", ...],
  "keywords_for_resume": ["keyword1", ...],
  "interview_prep_topics": ["topic1", ...]
}}

Be thorough but only include what's actually mentioned or strongly implied in the job description.

JSON Response:"""


# -----------------------------------------------------------------------------
# Resume Tailoring Prompt
# -----------------------------------------------------------------------------
RESUME_TAILORING_PROMPT = """You are an expert resume coach helping candidates tailor their resumes.

**Current Resume:**
{resume_text}

**Target Job Description:**
{job_description}

**Instructions:**
Analyze how well this resume matches the job and provide 4-6 specific improvement suggestions. For each suggestion, identify the EXACT text from their resume that should be changed, and provide a rewritten version.

You MUST return valid JSON with this exact structure:

{{
  "match_score": 75,
  "matching_strengths": ["Python experience", "API development"],
  "gaps": ["No cloud experience mentioned", "Missing CI/CD keywords"],
  "skills_to_add": ["AWS", "Docker", "Kubernetes"],
  "skills_to_emphasize": ["Python", "REST APIs", "PostgreSQL"],
  "suggestions": [
    {{
      "section": "Experience",
      "suggestion": "Reword this bullet point to add metrics and match job keywords",
      "current": "Worked on API development for the backend team",
      "example": "Designed and implemented RESTful APIs serving 50,000+ daily requests with 99.9% uptime, reducing response latency by 40% through Redis caching",
      "priority": "high",
      "reason": "The job emphasizes scalable systems - quantified achievements prove you can deliver at scale"
    }},
    {{
      "section": "Experience",
      "suggestion": "Strengthen this bullet with leadership language",
      "current": "Helped junior developers with code reviews",
      "example": "Mentored 3 junior developers through weekly code reviews and pair programming sessions, improving team velocity by 25%",
      "priority": "medium",
      "reason": "Senior roles require demonstrated mentorship experience"
    }},
    {{
      "section": "Skills",
      "suggestion": "Add cloud technologies to match job requirements",
      "current": null,
      "example": "Cloud & DevOps: AWS (EC2, S3, Lambda, RDS), Docker, Kubernetes, CI/CD",
      "priority": "high",
      "reason": "AWS is listed as a required skill in the job posting"
    }}
  ]
}}

IMPORTANT:
- For rewording suggestions: set "current" to the EXACT text from their resume that should be replaced
- For new additions: set "current" to null
- Every suggestion MUST include an "example" field with copy-paste ready replacement text
- Examples should transform their actual experience using the job description's language and keywords
- Include 4-6 suggestions covering different sections (Experience, Skills, Summary)
- Prioritize Experience bullet point rewrites - these have the highest impact

JSON Response:"""


# -----------------------------------------------------------------------------
# Prompt Registry - for viewing and live editing via API
# -----------------------------------------------------------------------------
ALL_PROMPTS = {
    "cover_letter": COVER_LETTER_PROMPT,
    "message_generation": MESSAGE_GENERATION_PROMPT,
    "skill_extraction": SKILL_EXTRACTION_PROMPT,
    "job_analysis": JOB_ANALYSIS_PROMPT,
    "resume_tailoring": RESUME_TAILORING_PROMPT,
}


def get_prompt(name: str) -> str:
    """Get a prompt template by name."""
    return ALL_PROMPTS.get(name, "")


def set_prompt(name: str, template: str) -> bool:
    """Update a prompt template at runtime (resets on restart)."""
    if name not in ALL_PROMPTS:
        return False
    ALL_PROMPTS[name] = template
    # Update the module-level variable so ai_service picks up the change
    globals()[{
        "cover_letter": "COVER_LETTER_PROMPT",
        "message_generation": "MESSAGE_GENERATION_PROMPT",
        "skill_extraction": "SKILL_EXTRACTION_PROMPT",
        "job_analysis": "JOB_ANALYSIS_PROMPT",
        "resume_tailoring": "RESUME_TAILORING_PROMPT",
    }[name]] = template
    return True
