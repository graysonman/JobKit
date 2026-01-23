"""
Resume and cover letter assistance service.
"""
import re
from typing import List, Dict, Optional

# Common technical skills to look for
TECH_SKILLS = {
    'languages': ['python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala'],
    'frontend': ['react', 'vue', 'angular', 'svelte', 'html', 'css', 'sass', 'tailwind', 'bootstrap', 'jquery'],
    'backend': ['node', 'express', 'fastapi', 'django', 'flask', 'spring', 'rails', '.net', 'laravel'],
    'databases': ['sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb', 'cassandra'],
    'cloud': ['aws', 'azure', 'gcp', 'heroku', 'vercel', 'netlify', 'cloudflare'],
    'devops': ['docker', 'kubernetes', 'terraform', 'ansible', 'jenkins', 'github actions', 'gitlab ci', 'circleci'],
    'tools': ['git', 'linux', 'agile', 'scrum', 'jira', 'confluence', 'figma', 'postman']
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
    required_section = re.search(r'(required|must have|requirements?)[\s:]*(.+?)(?=preferred|nice to have|bonus|$)', text, re.DOTALL)
    preferred_section = re.search(r'(preferred|nice to have|bonus|plus)[\s:]*(.+?)(?=responsibilities|about|$)', text, re.DOTALL)

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

    # Determine experience level
    experience_level = "entry-level"
    if re.search(r'\b(senior|lead|principal|staff)\b', text):
        experience_level = "senior"
    elif re.search(r'\b(mid[- ]?level|3-5|4-6|5\+)\s*years?\b', text):
        experience_level = "mid-level"
    elif re.search(r'\b(junior|entry[- ]?level|0-2|1-3)\s*years?\b', text):
        experience_level = "entry-level"

    # Extract key responsibilities (sentences with action verbs)
    responsibilities = []
    action_verbs = ['build', 'develop', 'design', 'implement', 'create', 'maintain', 'lead', 'collaborate', 'write', 'test', 'deploy', 'optimize']
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
        r'\b(startup|enterprise|b2b|b2c|saas|fintech|healthcare|e-commerce)\b',
        r'\b(remote|hybrid|onsite|on-site)\b',
        r'\b(full[- ]?time|part[- ]?time|contract)\b',
        r'\b(agile|scrum|kanban)\b'
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

    # Calculate match score
    if all_job_skills:
        match_score = len(matching_skills) / len(all_job_skills)
    else:
        match_score = 0.5  # Default if no skills detected

    # Generate suggestions
    suggestions = []

    if missing_skills:
        suggestions.append(f"Consider adding experience with: {', '.join(missing_skills[:5])}")

    if job_analysis["experience_level"] == "senior" and "lead" not in resume_lower and "senior" not in resume_lower:
        suggestions.append("Highlight leadership experience and senior-level responsibilities")

    if "metrics" not in resume_lower and "%" not in resume_text:
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
    custom_points: Optional[List[str]] = None
) -> str:
    """
    Generate a personalized cover letter.
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

    # Build cover letter
    cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {role} position at {company_name}. """

    if elevator_pitch:
        cover_letter += f"{elevator_pitch} "
    elif current_title:
        cover_letter += f"As a {current_title}"
        if experience:
            cover_letter += f" with {experience} years of experience"
        cover_letter += ", I am excited about the opportunity to contribute to your team. "

    cover_letter += "\n\n"

    # Skills paragraph
    if matching_skills:
        cover_letter += f"My experience with {', '.join(matching_skills[:4])} aligns well with your requirements. "

    if resume_summary:
        cover_letter += resume_summary + " "

    cover_letter += "\n\n"

    # Custom points
    if custom_points:
        cover_letter += "Specifically, I would like to highlight:\n"
        for point in custom_points[:3]:
            cover_letter += f"- {point}\n"
        cover_letter += "\n"

    # Closing
    cover_letter += f"""I am particularly drawn to {company_name} because of [specific reason - research the company]. I would welcome the opportunity to discuss how my skills and experience can contribute to your team's success.

Thank you for considering my application. I look forward to hearing from you.

Best regards,
{name}"""

    return cover_letter


def suggest_resume_tweaks(resume_text: str, job_description: str) -> List[Dict]:
    """
    Suggest specific changes to make resume better match job.

    Returns list of suggestions like:
        [
            {"section": "Experience", "suggestion": "Quantify your impact at Company X"},
            {"section": "Skills", "suggestion": "Add 'CI/CD' to match job requirements"}
        ]
    """
    suggestions = []
    analysis = analyze_resume_match(resume_text, job_description)

    # Skills suggestions
    if analysis["missing_skills"]:
        suggestions.append({
            "section": "Skills",
            "suggestion": f"Add these relevant skills if you have experience: {', '.join(analysis['missing_skills'][:5])}"
        })

    # Check for quantification
    if not re.search(r'\d+%|\d+x|\$\d+', resume_text):
        suggestions.append({
            "section": "Experience",
            "suggestion": "Add metrics and numbers to quantify your achievements (e.g., 'Reduced load time by 50%')"
        })

    # Check for action verbs
    weak_starts = ['responsible for', 'worked on', 'helped with', 'assisted']
    for weak in weak_starts:
        if weak in resume_text.lower():
            suggestions.append({
                "section": "Experience",
                "suggestion": f"Replace '{weak}' with stronger action verbs like 'Led', 'Developed', 'Implemented', 'Architected'"
            })
            break

    # Job-specific suggestions
    job_analysis = extract_keywords_from_job(job_description)

    if job_analysis["experience_level"] == "senior":
        suggestions.append({
            "section": "Summary",
            "suggestion": "Emphasize leadership, mentoring, and architectural decision-making experience"
        })

    if 'remote' in job_analysis["keywords"]:
        suggestions.append({
            "section": "Summary",
            "suggestion": "Mention remote work experience and self-management skills if applicable"
        })

    return suggestions[:5]
