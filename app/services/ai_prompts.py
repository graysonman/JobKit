"""
JobKit - AI Prompt Templates

Prompt templates for various AI-powered features.

# =============================================================================
# TODO: Local AI Integration (Feature 1) - Implement prompt templates
# =============================================================================

These prompts are designed for instruction-tuned models like:
- Mistral 7B Instruct
- Phi-3 Mini
- Llama 2 Chat
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

**Target Position:**
- Company: {company_name}
- Role: {role}

**Job Description:**
{job_description}

**Instructions:**
Write a {length} cover letter in a {tone} tone that:
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
Analyze how well this resume matches the job and provide specific improvement suggestions.

Return a JSON response with:

{{
  "match_score": 0-100,
  "matching_strengths": ["strength1", ...],
  "gaps": ["gap1", ...],
  "suggestions": [
    {{
      "section": "Summary|Experience|Skills|Education",
      "current": "current text if applicable",
      "suggested": "improved text",
      "reason": "why this change helps"
    }},
    ...
  ],
  "keywords_to_add": ["keyword1", ...],
  "keywords_to_emphasize": ["keyword1", ...]
}}

Focus on actionable, specific suggestions. Prioritize changes that will have the most impact on ATS matching and recruiter interest.

JSON Response:"""
