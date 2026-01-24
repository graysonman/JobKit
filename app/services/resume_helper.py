"""
JobKit - Resume and cover letter assistance service.

Provides job description analysis, resume matching, and cover letter generation
using keyword extraction and template-based generation.
"""
import re
from typing import List, Dict, Optional
from urllib.parse import urlparse

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
