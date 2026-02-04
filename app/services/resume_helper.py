"""
JobKit - Resume and cover letter assistance service.

Provides job description analysis, resume matching, cover letter generation,
and resume parsing using keyword extraction and template-based generation.

Features:
- Job description keyword extraction and analysis
- Resume-to-job matching with scoring
- Cover letter generation with tone/length options
- Resume parsing from text, PDF, DOCX, and TXT files
- Resume tailoring suggestions based on job requirements

AI-powered endpoints (cover letter generation, skill extraction, job analysis,
resume tailoring) are available via /api/resume/*-ai routes, which use
AIService with graceful fallback to keyword-based methods.

Resume parsing requires optional dependencies:
- PDF: pip install pdfplumber
- DOCX: pip install python-docx
"""
import re
import os
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass

# Import structured resume schemas
from ..schemas import StructuredResume, ResumeExperience, ResumeEducation, ResumeProject

# Expanded and categorized technical skills database
TECH_SKILLS = {
    'languages': [
        'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'golang',
        'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab',
        'perl', 'haskell', 'elixir', 'clojure', 'dart', 'lua', 'groovy',
        'objective-c', 'f#', 'julia', 'cobol', 'fortran', 'assembly'
    ],
    'frontend': [
        'react', 'reactjs', 'vue', 'vuejs', 'angular', 'angularjs', 'svelte',
        'html', 'html5', 'css', 'css3', 'sass', 'scss', 'less', 'tailwind',
        'tailwindcss', 'bootstrap', 'jquery', 'webpack', 'vite', 'parcel',
        'nextjs', 'next.js', 'nuxt', 'nuxtjs', 'gatsby', 'remix',
        'styled-components', 'emotion', 'material-ui', 'mui', 'chakra',
        'ant design', 'redux', 'mobx', 'zustand', 'recoil', 'pinia',
        'storybook', 'cypress', 'playwright', 'jest', 'testing-library',
        'figma', 'sketch', 'adobe xd', 'responsive design', 'accessibility', 'a11y',
        'pwa', 'web components', 'webgl', 'three.js', 'd3', 'd3.js'
    ],
    'backend': [
        'node', 'nodejs', 'express', 'expressjs', 'fastapi', 'django', 'flask',
        'spring', 'spring boot', 'rails', 'ruby on rails', '.net', 'asp.net',
        'laravel', 'symfony', 'gin', 'echo', 'fiber', 'fastify', 'nestjs',
        'koa', 'hapi', 'phoenix', 'actix', 'rocket', 'axum',
        'graphql', 'rest', 'restful', 'api', 'microservices', 'grpc',
        'websocket', 'socket.io', 'rabbitmq', 'kafka', 'celery', 'sidekiq',
        'oauth', 'jwt', 'authentication', 'authorization'
    ],
    'databases': [
        'sql', 'postgresql', 'postgres', 'mysql', 'mariadb', 'sqlite',
        'mongodb', 'mongo', 'redis', 'elasticsearch', 'elastic',
        'dynamodb', 'cassandra', 'couchdb', 'couchbase', 'neo4j',
        'oracle', 'sql server', 'mssql', 'firebase', 'firestore',
        'supabase', 'prisma', 'sequelize', 'typeorm', 'sqlalchemy',
        'mongoose', 'drizzle', 'knex', 'hasura', 'timescaledb',
        'influxdb', 'clickhouse', 'cockroachdb', 'planetscale'
    ],
    'cloud': [
        'aws', 'amazon web services', 'azure', 'microsoft azure',
        'gcp', 'google cloud', 'google cloud platform',
        'heroku', 'vercel', 'netlify', 'cloudflare', 'digital ocean',
        'linode', 'vultr', 'render', 'railway', 'fly.io',
        'ec2', 's3', 'lambda', 'cloudfront', 'route53', 'rds',
        'ecs', 'eks', 'fargate', 'elastic beanstalk',
        'api gateway', 'sqs', 'sns', 'kinesis', 'step functions'
    ],
    'devops': [
        'docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'puppet',
        'chef', 'vagrant', 'packer', 'helm', 'istio', 'envoy',
        'jenkins', 'github actions', 'gitlab ci', 'circleci', 'travis ci',
        'azure devops', 'bitbucket pipelines', 'argo cd', 'flux',
        'ci/cd', 'continuous integration', 'continuous deployment',
        'prometheus', 'grafana', 'datadog', 'new relic', 'splunk',
        'elk', 'logstash', 'kibana', 'cloudwatch', 'pagerduty',
        'nginx', 'apache', 'haproxy', 'traefik', 'caddy'
    ],
    'data_science': [
        'machine learning', 'ml', 'deep learning', 'dl', 'neural networks',
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn',
        'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn', 'plotly',
        'jupyter', 'jupyter notebook', 'colab', 'databricks',
        'spark', 'pyspark', 'hadoop', 'hive', 'presto', 'trino',
        'airflow', 'luigi', 'dagster', 'prefect', 'mlflow',
        'dbt', 'looker', 'tableau', 'power bi', 'metabase', 'superset',
        'nlp', 'natural language processing', 'computer vision', 'cv',
        'transformers', 'huggingface', 'langchain', 'openai', 'gpt',
        'llm', 'large language models', 'rag', 'vector database',
        'pinecone', 'weaviate', 'milvus', 'chromadb'
    ],
    'mobile': [
        'ios', 'android', 'react native', 'flutter', 'xamarin',
        'swift', 'swiftui', 'uikit', 'kotlin', 'jetpack compose',
        'cordova', 'ionic', 'capacitor', 'expo', 'nativescript',
        'mobile development', 'app development'
    ],
    'testing': [
        'testing', 'unit testing', 'integration testing', 'e2e testing',
        'tdd', 'test-driven development', 'bdd', 'behavior-driven',
        'jest', 'mocha', 'chai', 'jasmine', 'pytest', 'unittest',
        'rspec', 'junit', 'testng', 'selenium', 'puppeteer',
        'cypress', 'playwright', 'detox', 'appium',
        'postman', 'insomnia', 'api testing', 'load testing',
        'jmeter', 'locust', 'k6', 'artillery'
    ],
    'security': [
        'security', 'cybersecurity', 'infosec', 'appsec',
        'owasp', 'penetration testing', 'pen testing', 'vulnerability',
        'encryption', 'ssl', 'tls', 'https', 'certificates',
        'authentication', 'authorization', 'oauth', 'saml', 'sso',
        'identity management', 'iam', 'rbac', 'abac',
        'soc2', 'gdpr', 'hipaa', 'pci', 'compliance',
        'vault', 'secrets management', 'key management'
    ],
    'tools': [
        'git', 'github', 'gitlab', 'bitbucket', 'svn',
        'linux', 'unix', 'bash', 'shell', 'powershell', 'zsh',
        'vim', 'neovim', 'emacs', 'vscode', 'visual studio',
        'intellij', 'pycharm', 'webstorm', 'eclipse',
        'agile', 'scrum', 'kanban', 'safe', 'lean',
        'jira', 'confluence', 'notion', 'asana', 'trello',
        'slack', 'teams', 'zoom', 'figma', 'miro',
        'postman', 'swagger', 'openapi', 'api documentation'
    ],
    'soft_skills': [
        'leadership', 'management', 'mentoring', 'coaching',
        'communication', 'collaboration', 'teamwork',
        'problem solving', 'critical thinking', 'analytical',
        'project management', 'product management', 'stakeholder',
        'presentation', 'documentation', 'technical writing',
        'cross-functional', 'remote work', 'distributed teams'
    ]
}

# Flatten all skills for matching
ALL_SKILLS = []
for category in TECH_SKILLS.values():
    ALL_SKILLS.extend(category)


def extract_keywords_from_job(job_description: str) -> Dict:
    """
    Extract key requirements from a job description.

    Returns:
        {
            "required_skills": ["python", "sql", ...],
            "preferred_skills": ["aws", "docker", ...],
            "experience_level": "mid-level",
            "key_responsibilities": [...],
            "keywords": [...]
        }
    """
    if not job_description:
        return {
            "required_skills": [],
            "preferred_skills": [],
            "experience_level": "unknown",
            "key_responsibilities": [],
            "keywords": []
        }

    text = job_description.lower()

    # Extract skills
    found_skills = []
    for skill in ALL_SKILLS:
        # Match whole words only
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text):
            found_skills.append(skill)

    # Categorize into required vs preferred
    required_skills = []
    preferred_skills = []

    # Look for required section
    required_section = re.search(r'(required|must have|requirements?|qualifications?)[\s:]*(.+?)(?=preferred|nice to have|bonus|plus|$)', text, re.DOTALL)
    preferred_section = re.search(r'(preferred|nice to have|bonus|plus|desired)[\s:]*(.+?)(?=responsibilities|about|what you|who you|$)', text, re.DOTALL)

    if required_section:
        required_text = required_section.group(2)
        for skill in found_skills:
            if skill in required_text:
                required_skills.append(skill)

    if preferred_section:
        preferred_text = preferred_section.group(2)
        for skill in found_skills:
            if skill in preferred_text and skill not in required_skills:
                preferred_skills.append(skill)

    # If no clear sections, all found skills are considered required
    if not required_skills and not preferred_skills:
        required_skills = found_skills

    # Remaining skills go to preferred
    for skill in found_skills:
        if skill not in required_skills and skill not in preferred_skills:
            preferred_skills.append(skill)

    # Determine experience level
    experience_level = "entry-level"
    if re.search(r'\b(senior|lead|principal|staff|architect)\b', text):
        experience_level = "senior"
    elif re.search(r'\b(mid[- ]?level|3-5|4-6|5\+|3\+|4\+)\s*years?\b', text):
        experience_level = "mid-level"
    elif re.search(r'\b(junior|entry[- ]?level|0-2|1-3|associate|graduate)\s*(years?)?\b', text):
        experience_level = "entry-level"
    elif re.search(r'\b(7-10|8\+|10\+)\s*years?\b', text):
        experience_level = "senior"

    # Extract key responsibilities (sentences with action verbs)
    responsibilities = []
    action_verbs = [
        'build', 'develop', 'design', 'implement', 'create', 'maintain',
        'lead', 'collaborate', 'write', 'test', 'deploy', 'optimize',
        'architect', 'scale', 'manage', 'mentor', 'review', 'troubleshoot',
        'analyze', 'integrate', 'automate', 'improve', 'ensure', 'support'
    ]
    sentences = re.split(r'[.•\n]', job_description)
    for sentence in sentences:
        sentence = sentence.strip()
        if any(verb in sentence.lower() for verb in action_verbs) and len(sentence) > 20:
            responsibilities.append(sentence)
            if len(responsibilities) >= 5:
                break

    # Extract other important keywords
    keywords = []
    keyword_patterns = [
        r'\b(startup|enterprise|b2b|b2c|saas|fintech|healthcare|e-commerce|edtech|martech)\b',
        r'\b(remote|hybrid|onsite|on-site|in-office)\b',
        r'\b(full[- ]?time|part[- ]?time|contract|contractor|freelance)\b',
        r'\b(agile|scrum|kanban|waterfall)\b',
        r'\b(fast[- ]?paced|high[- ]?growth|early[- ]?stage|series [a-d])\b'
    ]
    for pattern in keyword_patterns:
        matches = re.findall(pattern, text)
        keywords.extend(matches)

    return {
        "required_skills": list(set(required_skills)),
        "preferred_skills": list(set(preferred_skills)),
        "experience_level": experience_level,
        "key_responsibilities": responsibilities[:5],
        "keywords": list(set(keywords))
    }


def analyze_resume_match(resume_text: str, job_description: str) -> Dict:
    """
    Analyze how well a resume matches a job description.

    Returns:
        {
            "match_score": 0.75,
            "matching_skills": [...],
            "missing_skills": [...],
            "suggestions": [...]
        }
    """
    if not resume_text or not job_description:
        return {
            "match_score": 0,
            "matching_skills": [],
            "missing_skills": [],
            "suggestions": ["Please provide both resume and job description"]
        }

    job_analysis = extract_keywords_from_job(job_description)
    resume_lower = resume_text.lower()

    # Find matching and missing skills
    matching_skills = []
    missing_skills = []

    all_job_skills = job_analysis["required_skills"] + job_analysis["preferred_skills"]

    for skill in all_job_skills:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, resume_lower):
            matching_skills.append(skill)
        else:
            missing_skills.append(skill)

    # Calculate match score with weighted scoring
    # Required skills count more than preferred
    required_match = sum(1 for s in job_analysis["required_skills"] if s in matching_skills)
    preferred_match = sum(1 for s in job_analysis["preferred_skills"] if s in matching_skills)

    required_total = len(job_analysis["required_skills"])
    preferred_total = len(job_analysis["preferred_skills"])

    if required_total + preferred_total > 0:
        # Required skills weight: 0.7, Preferred: 0.3
        required_score = (required_match / required_total) if required_total > 0 else 0.5
        preferred_score = (preferred_match / preferred_total) if preferred_total > 0 else 0.5
        match_score = (required_score * 0.7) + (preferred_score * 0.3)
    else:
        match_score = 0.5  # Default if no skills detected

    # Generate suggestions
    suggestions = []

    if missing_skills:
        # Prioritize required missing skills
        required_missing = [s for s in missing_skills if s in job_analysis["required_skills"]]
        if required_missing:
            suggestions.append(f"Critical: Add experience with required skills: {', '.join(required_missing[:4])}")
        preferred_missing = [s for s in missing_skills if s in job_analysis["preferred_skills"]][:3]
        if preferred_missing:
            suggestions.append(f"Consider adding: {', '.join(preferred_missing)}")

    if job_analysis["experience_level"] == "senior":
        if "lead" not in resume_lower and "senior" not in resume_lower and "architect" not in resume_lower:
            suggestions.append("Highlight leadership experience and senior-level responsibilities")
        if "mentor" not in resume_lower:
            suggestions.append("Add mentoring experience if applicable")

    if "metrics" not in resume_lower and "%" not in resume_text and not re.search(r'\d+x', resume_lower):
        suggestions.append("Add quantifiable achievements (e.g., 'Improved performance by 40%')")

    for keyword in job_analysis["keywords"]:
        if keyword not in resume_lower:
            suggestions.append(f"Consider mentioning '{keyword}' if relevant to your experience")

    return {
        "match_score": round(match_score, 2),
        "matching_skills": matching_skills,
        "missing_skills": missing_skills,
        "suggestions": suggestions[:5]
    }


def generate_cover_letter(
    user_profile: Dict,
    job_description: str,
    company_name: str,
    role: str,
    custom_points: Optional[List[str]] = None,
    tone: str = "professional",
    length: str = "medium"
) -> str:
    """
    Generate a personalized cover letter.

    Args:
        tone: professional, conversational, enthusiastic, or formal
        length: short (~150 words), medium (~250 words), or detailed (~350 words)
    """
    name = user_profile.get("name", "")
    current_title = user_profile.get("current_title", "software developer")
    skills = user_profile.get("skills", "")
    experience = user_profile.get("years_experience", "")
    resume_summary = user_profile.get("resume_summary", "")
    elevator_pitch = user_profile.get("elevator_pitch", "")

    # Extract key requirements from job
    job_analysis = extract_keywords_from_job(job_description)
    matching_skills = [s for s in job_analysis["required_skills"] if s.lower() in skills.lower()]

    # Tone-specific openings and closings
    tone_openers = {
        "professional": f"I am writing to express my interest in the {role} position at {company_name}.",
        "conversational": f"I was excited to see the {role} opening at {company_name} and knew I had to reach out.",
        "enthusiastic": f"I'm thrilled to apply for the {role} position at {company_name}! This opportunity is exactly what I've been looking for.",
        "formal": f"I respectfully submit my application for the {role} position currently available at {company_name}."
    }

    tone_closings = {
        "professional": "I would welcome the opportunity to discuss how my skills and experience can contribute to your team's success.",
        "conversational": "I'd love to chat more about how I could help your team. Let's connect!",
        "enthusiastic": "I'm genuinely excited about this opportunity and can't wait to discuss how I can make an impact at your company!",
        "formal": "I would be honored to discuss my qualifications further at your earliest convenience."
    }

    tone_signoffs = {
        "professional": "Best regards",
        "conversational": "Looking forward to connecting",
        "enthusiastic": "With enthusiasm",
        "formal": "Respectfully yours"
    }

    # Build cover letter
    opener = tone_openers.get(tone, tone_openers["professional"])
    closer = tone_closings.get(tone, tone_closings["professional"])
    signoff = tone_signoffs.get(tone, tone_signoffs["professional"])

    cover_letter = f"Dear Hiring Manager,\n\n{opener} "

    # Introduction based on profile
    if elevator_pitch:
        cover_letter += f"{elevator_pitch} "
    elif current_title:
        cover_letter += f"As a {current_title}"
        if experience:
            cover_letter += f" with {experience} years of experience"
        cover_letter += ", I am confident I can contribute meaningfully to your team. "

    cover_letter += "\n\n"

    # Skills paragraph
    if matching_skills:
        skill_intro = {
            "professional": "My experience with",
            "conversational": "I've worked extensively with",
            "enthusiastic": "I'm passionate about working with",
            "formal": "My technical proficiency includes"
        }
        intro = skill_intro.get(tone, skill_intro["professional"])
        cover_letter += f"{intro} {', '.join(matching_skills[:4])} aligns well with your requirements. "

    # Add resume summary for medium/detailed length
    if length in ["medium", "detailed"] and resume_summary:
        cover_letter += resume_summary + " "

    cover_letter += "\n\n"

    # Custom points (more for detailed, fewer for short)
    if custom_points:
        max_points = {"short": 2, "medium": 3, "detailed": 4}.get(length, 3)
        cover_letter += "Key highlights from my background:\n"
        for point in custom_points[:max_points]:
            cover_letter += f"- {point}\n"
        cover_letter += "\n"

    # Additional detail for detailed length
    if length == "detailed" and job_analysis.get("key_responsibilities"):
        responsibilities = job_analysis["key_responsibilities"][:2]
        if responsibilities:
            cover_letter += "I am particularly prepared to take on responsibilities such as "
            cover_letter += " and ".join(responsibilities[:2]) + ". "
            cover_letter += "\n\n"

    # Closing
    cover_letter += f"I am particularly drawn to {company_name} because of [specific reason - research the company]. {closer}\n\n"

    if length == "short":
        cover_letter += f"Thank you for your time.\n\n{signoff},\n{name}"
    else:
        cover_letter += f"Thank you for considering my application. I look forward to hearing from you.\n\n{signoff},\n{name}"

    return cover_letter


def suggest_resume_tweaks(resume_text: str, job_description: str) -> List[Dict]:
    """
    Suggest specific changes to make resume better match job.

    Returns list of suggestions like:
        [
            {"section": "Experience", "suggestion": "Quantify your impact at Company X", "priority": "high"},
            {"section": "Skills", "suggestion": "Add 'CI/CD' to match job requirements", "priority": "medium"}
        ]
    """
    suggestions = []
    analysis = analyze_resume_match(resume_text, job_description)
    job_analysis = extract_keywords_from_job(job_description)

    # Skills suggestions (high priority for required, medium for preferred)
    required_missing = [s for s in analysis["missing_skills"] if s in job_analysis["required_skills"]]
    if required_missing:
        suggestions.append({
            "section": "Skills",
            "suggestion": f"Add these required skills if you have experience: {', '.join(required_missing[:4])}",
            "priority": "high"
        })

    preferred_missing = [s for s in analysis["missing_skills"] if s in job_analysis["preferred_skills"]]
    if preferred_missing:
        suggestions.append({
            "section": "Skills",
            "suggestion": f"Consider adding these preferred skills: {', '.join(preferred_missing[:3])}",
            "priority": "medium"
        })

    # Check for quantification
    if not re.search(r'\d+%|\d+x|\$\d+|\d+ (million|thousand|users?|customers?|requests?)', resume_text.lower()):
        suggestions.append({
            "section": "Experience",
            "suggestion": "Add metrics and numbers to quantify your achievements (e.g., 'Reduced load time by 50%', 'Served 1M users')",
            "priority": "high"
        })

    # Check for action verbs
    weak_starts = ['responsible for', 'worked on', 'helped with', 'assisted', 'participated in', 'involved in']
    for weak in weak_starts:
        if weak in resume_text.lower():
            suggestions.append({
                "section": "Experience",
                "suggestion": f"Replace '{weak}' with stronger action verbs like 'Led', 'Developed', 'Implemented', 'Architected', 'Spearheaded'",
                "priority": "medium"
            })
            break

    # Job-specific suggestions
    if job_analysis["experience_level"] == "senior":
        if "lead" not in resume_text.lower() and "led" not in resume_text.lower():
            suggestions.append({
                "section": "Summary",
                "suggestion": "Emphasize leadership experience - mention teams led, projects owned, or architectural decisions made",
                "priority": "high"
            })
        if "mentor" not in resume_text.lower():
            suggestions.append({
                "section": "Experience",
                "suggestion": "Add mentoring experience (junior developers coached, interns supervised, etc.)",
                "priority": "medium"
            })

    if 'remote' in job_analysis["keywords"]:
        if 'remote' not in resume_text.lower():
            suggestions.append({
                "section": "Summary",
                "suggestion": "Mention remote work experience and self-management skills if applicable",
                "priority": "low"
            })

    # Check for technical depth
    if job_analysis["experience_level"] in ["mid-level", "senior"]:
        if not re.search(r'(architected|designed|built from scratch|scaled|optimized)', resume_text.lower()):
            suggestions.append({
                "section": "Experience",
                "suggestion": "Include examples of system design, architecture decisions, or scaling challenges you've tackled",
                "priority": "medium"
            })

    # Check for impact language
    impact_words = ['increased', 'decreased', 'improved', 'reduced', 'saved', 'generated', 'grew', 'achieved']
    if not any(word in resume_text.lower() for word in impact_words):
        suggestions.append({
            "section": "Experience",
            "suggestion": "Use impact-focused language: 'Improved X by Y%', 'Reduced Z resulting in...'",
            "priority": "medium"
        })

    return suggestions[:6]


def get_skill_category(skill: str) -> Optional[str]:
    """
    Get the category of a skill.

    Returns category name or None if not found.
    """
    skill_lower = skill.lower()
    for category, skills in TECH_SKILLS.items():
        if skill_lower in skills:
            return category
    return None


def get_related_skills(skill: str) -> List[str]:
    """
    Get skills related to the given skill (from same category).

    Returns list of related skills.
    """
    category = get_skill_category(skill)
    if category:
        return [s for s in TECH_SKILLS[category] if s.lower() != skill.lower()][:10]
    return []


def extract_years_of_experience(resume_text: str) -> Optional[int]:
    """
    Try to extract years of experience from resume text.

    Returns estimated years or None.
    """
    # Look for explicit mentions
    patterns = [
        r'(\d+)\+?\s*years?\s*(of\s*)?(professional\s*)?(experience|expertise)',
        r'(experience|expertise)[:.\s]*(\d+)\+?\s*years?',
        r'(\d+)\s*years?\s*in\s*(software|tech|development|engineering)',
    ]

    for pattern in patterns:
        match = re.search(pattern, resume_text.lower())
        if match:
            # Extract the number from the match
            groups = match.groups()
            for g in groups:
                if g and g.isdigit():
                    return int(g)

    # Try to infer from work history dates
    year_pattern = r'(20\d{2}|19\d{2})'
    years = re.findall(year_pattern, resume_text)
    if years:
        years = [int(y) for y in years]
        if len(years) >= 2:
            # Estimate from date range
            return max(years) - min(years)

    return None


# =============================================
# Resume Parser Implementation
# =============================================

# Section header patterns (case-insensitive matching)
SECTION_HEADERS = {
    'summary': [
        r'^(?:professional\s+)?summary\b',
        r'^profile\b',
        r'^(?:career\s+)?objective\b',
        r'^about\s*(?:me)?\b',
        r'^overview\b'
    ],
    'experience': [
        r'^(?:work\s+|professional\s+)?experience\b',
        r'^(?:work\s+)?history\b',
        r'^employment\b',
        r'^career\s+history\b',
        r'^positions?\s+held\b'
    ],
    'education': [
        r'^education\b',
        r'^academic\s*(?:background)?\b',
        r'^degrees?\b',
        r'^qualifications?\b'
    ],
    'skills': [
        r'^(?:technical\s+|core\s+)?skills?\b',
        r'^(?:technical\s+)?competenc(?:ies|y)\b',
        r'^technologies\b',
        r'^expertise\b',
        r'^proficienc(?:ies|y)\b',
        r'^tools?\s*(?:&|and)?\s*technologies\b'
    ],
    'projects': [
        r'^(?:personal\s+|side\s+)?projects?\b',
        r'^portfolio\b',
        r'^selected\s+projects?\b'
    ],
    'certifications': [
        r'^certifications?\b',
        r'^licenses?\s*(?:&|and)?\s*certifications?\b',
        r'^professional\s+certifications?\b',
        r'^credentials?\b'
    ]
}

# Date patterns for parsing experience/education dates
DATE_PATTERNS = [
    # "Jan 2020 - Present" or "January 2020 - Dec 2022"
    r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\s*[-–—to]+\s*((?:Present|Current|Now)|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})',
    # "2020 - Present" or "2020 - 2022"
    r'(\d{4})\s*[-–—to]+\s*((?:Present|Current|Now)|\d{4})',
    # "01/2020 - 12/2022"
    r'(\d{1,2}/\d{4})\s*[-–—to]+\s*((?:Present|Current|Now)|\d{1,2}/\d{4})',
]


def _detect_section(line: str) -> Optional[str]:
    """Detect if a line is a section header."""
    line_clean = line.strip().rstrip(':').lower()

    # Skip very long lines (headers are usually short)
    if len(line_clean) > 50:
        return None

    for section_type, patterns in SECTION_HEADERS.items():
        for pattern in patterns:
            if re.match(pattern, line_clean, re.IGNORECASE):
                return section_type
    return None


def _parse_date_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract start and end dates from text."""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start_date = match.group(1).strip()
            end_date = match.group(2).strip()
            # Normalize "Present", "Current", "Now"
            if end_date.lower() in ('present', 'current', 'now'):
                end_date = 'Present'
            return start_date, end_date
    return None, None


def _extract_experience_entry(lines: List[str]) -> Optional[ResumeExperience]:
    """Parse lines into an experience entry."""
    if not lines:
        return None

    # Find the title line (first non-date line)
    first_line = ""
    for line in lines[:3]:  # Check first 3 lines
        line = line.strip()
        # Skip lines that look like pure date lines
        if _parse_date_range(line)[0] and not any(word in line.lower() for word in
            ['engineer', 'developer', 'manager', 'lead', 'architect', 'analyst',
             'designer', 'intern', 'director', 'specialist', 'consultant']):
            continue
        if line:
            first_line = line
            break

    if not first_line and lines:
        first_line = lines[0].strip()

    # Common patterns: "Title at Company" or "Company - Title" or "Title | Company"
    title = ""
    company = ""

    # Try "at" pattern
    at_match = re.match(r'^(.+?)\s+at\s+(.+?)(?:\s*[-–|]|$)', first_line, re.IGNORECASE)
    if at_match:
        title = at_match.group(1).strip()
        company = at_match.group(2).strip()
    else:
        # Try "Company - Title" or "Title - Company" pattern (but not date ranges)
        # Skip if line looks like a date range
        if not re.match(r'^\w{3,9}\s+\d{4}\s*[-–]', first_line) and not re.match(r'^\d{4}\s*[-–]', first_line):
            dash_match = re.match(r'^(.+?)\s*[-–|]\s*(.+?)(?:\s*[-–|]|$)', first_line)
            if dash_match:
                part1 = dash_match.group(1).strip()
                part2 = dash_match.group(2).strip()
                # Heuristic: if part1 looks like a title (has common title words), it's title-company
                title_words = ['engineer', 'developer', 'manager', 'lead', 'architect', 'analyst',
                              'designer', 'intern', 'director', 'specialist', 'consultant', 'senior', 'junior']
                if any(word in part1.lower() for word in title_words):
                    title, company = part1, part2
                else:
                    company, title = part1, part2
            else:
                # Use first line as title, company unknown
                title = first_line
        else:
            title = first_line

    # Look for dates in first few lines
    start_date, end_date = None, None
    location = None

    for line in lines[:3]:
        if not start_date:
            start_date, end_date = _parse_date_range(line)
        # Look for location patterns (City, State or City, Country)
        loc_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2}|[A-Z][a-z]+)\b', line)
        if loc_match and not location:
            location = f"{loc_match.group(1)}, {loc_match.group(2)}"

    # Collect bullet points
    bullets = []
    for line in lines[1:]:
        line = line.strip()
        # Skip empty lines and date lines
        if not line or _parse_date_range(line)[0]:
            continue
        # Remove bullet markers
        line = re.sub(r'^[\s•\-\*▪◦→]+', '', line).strip()
        if line and len(line) > 10:  # Skip very short lines
            bullets.append(line)

    if not title and not company:
        return None

    return ResumeExperience(
        company=company or "Unknown Company",
        title=title or "Unknown Title",
        start_date=start_date,
        end_date=end_date,
        location=location,
        bullets=bullets[:10]  # Limit bullets
    )


def _extract_education_entry(lines: List[str]) -> Optional[ResumeEducation]:
    """Parse lines into an education entry."""
    if not lines:
        return None

    school = ""
    degree = ""
    field = ""
    year = None
    gpa = None

    full_text = ' '.join(lines)

    # Extract school name (usually first line or contains "University", "College", etc.)
    for line in lines:
        line = line.strip()
        if any(word in line for word in ['University', 'College', 'Institute', 'School', 'Academy']):
            school = line.split(',')[0].split('|')[0].split('-')[0].strip()
            break
    if not school and lines:
        school = lines[0].strip()

    # Extract degree patterns
    degree_patterns = [
        r"(Bachelor'?s?|Master'?s?|Ph\.?D\.?|Doctor(?:ate)?|Associate'?s?|MBA|M\.?S\.?|B\.?S\.?|B\.?A\.?|M\.?A\.?)",
        r"(B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|Ph\.?D\.?)[\s,]+(?:in\s+)?([A-Za-z\s]+?)(?:\s*[-,|]|$)",
    ]

    for pattern in degree_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            degree = match.group(1).strip()
            if len(match.groups()) > 1 and match.group(2):
                field = match.group(2).strip()
            break

    # Extract year (graduation year)
    year_match = re.search(r'\b(20\d{2}|19\d{2})\b', full_text)
    if year_match:
        year = year_match.group(1)

    # Extract GPA
    gpa_match = re.search(r'GPA[:\s]*(\d+\.?\d*)', full_text, re.IGNORECASE)
    if gpa_match:
        gpa = gpa_match.group(1)

    if not school:
        return None

    return ResumeEducation(
        school=school,
        degree=degree or None,
        field=field or None,
        year=year,
        gpa=gpa
    )


def _extract_skills(text: str) -> List[str]:
    """Extract skills from a skills section text."""
    skills = []

    # Split by common delimiters
    parts = re.split(r'[,;•\-\*▪◦|/\n]+', text)

    for part in parts:
        part = part.strip()
        # Clean up and filter
        if part and 3 < len(part) < 50:  # Reasonable skill name length
            # Skip lines that look like section headers
            if not _detect_section(part):
                skills.append(part)

    # Also match known skills from our database
    text_lower = text.lower()
    for skill in ALL_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower) and skill not in [s.lower() for s in skills]:
            skills.append(skill)

    return list(set(skills))[:50]  # Dedupe and limit


def _extract_projects(lines: List[str]) -> List[ResumeProject]:
    """Extract project entries from project section lines."""
    projects = []
    current_project_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_project_lines:
                project = _parse_project(current_project_lines)
                if project:
                    projects.append(project)
                current_project_lines = []
            continue

        # Detect new project (usually a title line)
        # Heuristic: short lines without bullets that look like titles
        is_new_project = (
            len(line) < 80 and
            not line.startswith(('•', '-', '*', '▪', '◦')) and
            (line[0].isupper() or line.startswith('"'))
        )

        if is_new_project and current_project_lines:
            project = _parse_project(current_project_lines)
            if project:
                projects.append(project)
            current_project_lines = [line]
        else:
            current_project_lines.append(line)

    # Don't forget the last project
    if current_project_lines:
        project = _parse_project(current_project_lines)
        if project:
            projects.append(project)

    return projects[:10]  # Limit


def _parse_project(lines: List[str]) -> Optional[ResumeProject]:
    """Parse project lines into a ResumeProject."""
    if not lines:
        return None

    name = lines[0].strip()
    description = ""
    technologies = []
    url = None

    for line in lines[1:]:
        line = line.strip()
        # Look for URL
        url_match = re.search(r'https?://[^\s]+', line)
        if url_match:
            url = url_match.group(0)
            line = line.replace(url, '').strip()

        # Look for technologies line
        if re.match(r'^(?:tech(?:nologies)?|built with|stack|tools)[:\s]*', line, re.IGNORECASE):
            tech_text = re.sub(r'^(?:tech(?:nologies)?|built with|stack|tools)[:\s]*', '', line, flags=re.IGNORECASE)
            technologies = [t.strip() for t in re.split(r'[,;|]+', tech_text) if t.strip()]
        else:
            # Add to description
            line = re.sub(r'^[\s•\-\*▪◦→]+', '', line).strip()
            if line:
                description += line + " "

    if not name:
        return None

    return ResumeProject(
        name=name,
        description=description.strip() or None,
        technologies=technologies,
        url=url
    )


def parse_resume_text(text: str) -> StructuredResume:
    """
    Parse raw resume text into a StructuredResume object.

    Identifies sections and extracts structured data from each.
    """
    if not text:
        return StructuredResume(raw_text=text)

    lines = text.split('\n')

    # Identify sections
    sections = {}
    current_section = 'header'  # Content before first section header
    current_lines = []

    for line in lines:
        section_type = _detect_section(line)
        if section_type:
            # Save previous section
            if current_lines:
                if current_section not in sections:
                    sections[current_section] = []
                sections[current_section].extend(current_lines)
            current_section = section_type
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_lines:
        if current_section not in sections:
            sections[current_section] = []
        sections[current_section].extend(current_lines)

    # Parse each section
    summary = None
    experience = []
    education = []
    skills = []
    projects = []
    certifications = []

    # Summary
    if 'summary' in sections:
        summary_text = '\n'.join(sections['summary']).strip()
        # Clean up and limit length
        summary = ' '.join(summary_text.split())[:2000]

    # Experience - split into entries (by empty lines or patterns)
    if 'experience' in sections:
        exp_lines = sections['experience']
        entries = _split_into_entries(exp_lines)
        for entry_lines in entries:
            exp = _extract_experience_entry(entry_lines)
            if exp:
                experience.append(exp)

    # Education
    if 'education' in sections:
        edu_lines = sections['education']
        entries = _split_into_entries(edu_lines)
        for entry_lines in entries:
            edu = _extract_education_entry(entry_lines)
            if edu:
                education.append(edu)

    # Skills
    if 'skills' in sections:
        skills_text = '\n'.join(sections['skills'])
        skills = _extract_skills(skills_text)

    # Projects
    if 'projects' in sections:
        projects = _extract_projects(sections['projects'])

    # Certifications (simpler - just a list)
    if 'certifications' in sections:
        for line in sections['certifications']:
            line = line.strip()
            line = re.sub(r'^[\s•\-\*▪◦→]+', '', line).strip()
            if line and len(line) > 3:
                certifications.append(line)

    return StructuredResume(
        summary=summary,
        experience=experience,
        education=education,
        skills=skills,
        projects=projects,
        certifications=certifications[:20],  # Limit
        raw_text=text
    )


def _split_into_entries(lines: List[str]) -> List[List[str]]:
    """Split section lines into individual entries based on patterns."""
    entries = []
    current_entry = []
    had_empty_line = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            had_empty_line = True
            continue

        # Check if this looks like a new entry start:
        # - After an empty line AND
        # - Line contains title words OR is followed by a date line
        is_new_entry = False

        if had_empty_line and current_entry:
            title_words = ['engineer', 'developer', 'manager', 'lead', 'architect', 'analyst',
                          'designer', 'intern', 'director', 'specialist', 'consultant', 'senior', 'junior']
            has_title_word = any(word in stripped.lower() for word in title_words)

            # Check if this line or next line has a date
            has_date_nearby = _parse_date_range(stripped)[0] is not None
            if i + 1 < len(lines):
                has_date_nearby = has_date_nearby or _parse_date_range(lines[i + 1].strip())[0] is not None

            # Also check if line starts with a company/title pattern (not a bullet)
            is_not_bullet = not stripped.startswith(('•', '-', '*', '▪', '◦', '→'))

            if (has_title_word or has_date_nearby) and is_not_bullet:
                is_new_entry = True

        if is_new_entry:
            entries.append(current_entry)
            current_entry = [line]
        else:
            current_entry.append(line)

        had_empty_line = False

    if current_entry:
        entries.append(current_entry)

    return entries


def parse_resume_file(file_path: str) -> StructuredResume:
    """
    Parse a resume file (PDF, DOCX, or TXT) into a StructuredResume object.

    Requires:
    - PDF: pip install pdfplumber
    - DOCX: pip install python-docx
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

    elif ext == '.pdf':
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                text = '\n'.join(pages_text)
        except ImportError:
            raise ImportError(
                "PDF parsing requires pdfplumber. Install with: pip install pdfplumber"
            )

    elif ext in ['.docx', '.doc']:
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            text = '\n'.join(paragraphs)
        except ImportError:
            raise ImportError(
                "DOCX parsing requires python-docx. Install with: pip install python-docx"
            )

    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .txt, .pdf, .docx")

    return parse_resume_text(text)


@dataclass
class TailoredSuggestion:
    """A suggestion for tailoring the resume to a job."""
    section: str
    original: Optional[str]
    suggestion: str
    priority: str  # high, medium, low
    reason: str


@dataclass
class TailoredResume:
    """Result of tailoring a resume to a job description."""
    resume: StructuredResume
    suggestions: List[TailoredSuggestion]
    keywords_to_add: List[str]
    skills_to_emphasize: List[str]
    skills_to_add: List[str]
    match_score: float


def tailor_resume_for_job(resume: StructuredResume, job_description: str) -> TailoredResume:
    """
    Analyze resume against job description and provide tailoring suggestions.

    Returns a TailoredResume with the original resume and suggestions for improvement.
    """
    suggestions = []

    # Get job analysis
    job_analysis = extract_keywords_from_job(job_description)

    # Build resume text for matching
    resume_text_parts = []
    if resume.summary:
        resume_text_parts.append(resume.summary)
    for exp in resume.experience:
        resume_text_parts.append(f"{exp.title} {exp.company}")
        resume_text_parts.extend(exp.bullets)
    resume_text_parts.extend(resume.skills)
    resume_text = ' '.join(resume_text_parts).lower()

    # Find matching and missing skills
    all_job_skills = job_analysis["required_skills"] + job_analysis["preferred_skills"]
    matching_skills = [s for s in all_job_skills if s.lower() in resume_text]
    missing_skills = [s for s in all_job_skills if s.lower() not in resume_text]

    # Skills suggestions
    required_missing = [s for s in missing_skills if s in job_analysis["required_skills"]]
    preferred_missing = [s for s in missing_skills if s in job_analysis["preferred_skills"]]

    if required_missing:
        suggestions.append(TailoredSuggestion(
            section="Skills",
            original=None,
            suggestion=f"Add these required skills if you have experience: {', '.join(required_missing[:5])}",
            priority="high",
            reason="These skills are listed as required in the job posting"
        ))

    if preferred_missing:
        suggestions.append(TailoredSuggestion(
            section="Skills",
            original=None,
            suggestion=f"Consider adding these preferred skills: {', '.join(preferred_missing[:4])}",
            priority="medium",
            reason="These are listed as preferred/nice-to-have skills"
        ))

    # Reorder skills - put matching required skills first
    skills_to_emphasize = [s for s in resume.skills if s.lower() in [ms.lower() for ms in matching_skills]]

    # Summary suggestions
    if resume.summary:
        if job_analysis["experience_level"] == "senior":
            if "lead" not in resume.summary.lower() and "senior" not in resume.summary.lower():
                suggestions.append(TailoredSuggestion(
                    section="Summary",
                    original=resume.summary[:100] + "...",
                    suggestion="Emphasize leadership and senior-level experience in your summary",
                    priority="high",
                    reason="This is a senior position requiring demonstrated leadership"
                ))
    else:
        suggestions.append(TailoredSuggestion(
            section="Summary",
            original=None,
            suggestion="Add a professional summary highlighting your fit for this role",
            priority="high",
            reason="A targeted summary helps immediately show your relevance"
        ))

    # Experience bullet suggestions
    for exp in resume.experience:
        has_metrics = any(
            re.search(r'\d+%|\d+x|\$\d+|\d+ (users?|customers?|requests?)', bullet.lower())
            for bullet in exp.bullets
        )
        if not has_metrics:
            suggestions.append(TailoredSuggestion(
                section="Experience",
                original=f"{exp.title} at {exp.company}",
                suggestion="Add quantifiable metrics to your bullet points (e.g., 'Improved performance by 40%')",
                priority="medium",
                reason="Metrics make achievements concrete and memorable"
            ))
            break  # One suggestion per issue

    # Check for weak action verbs
    weak_verbs = ['responsible for', 'worked on', 'helped with', 'assisted']
    for exp in resume.experience:
        for bullet in exp.bullets:
            for weak in weak_verbs:
                if weak in bullet.lower():
                    suggestions.append(TailoredSuggestion(
                        section="Experience",
                        original=bullet[:80] + "..." if len(bullet) > 80 else bullet,
                        suggestion=f"Replace '{weak}' with stronger action verbs like 'Led', 'Developed', 'Implemented'",
                        priority="medium",
                        reason="Strong action verbs demonstrate initiative and impact"
                    ))
                    break
            if len(suggestions) > 10:
                break
        if len(suggestions) > 10:
            break

    # Calculate match score
    if all_job_skills:
        match_score = len(matching_skills) / len(all_job_skills)
    else:
        match_score = 0.5

    return TailoredResume(
        resume=resume,
        suggestions=suggestions[:10],  # Limit suggestions
        keywords_to_add=missing_skills[:10],
        skills_to_emphasize=skills_to_emphasize,
        skills_to_add=required_missing + preferred_missing[:5],
        match_score=round(match_score, 2)
    )
