"""
JobKit - Message generation service.

Creates personalized outreach messages for networking contacts
using templates with placeholder substitution.
"""
from ..models import MessageTemplate, Contact, UserProfile
from typing import Optional, List, Dict
import re
import random

# Platform character limits
PLATFORM_LIMITS = {
    "linkedin_connection": 300,
    "linkedin_inmail": 1900,
    "linkedin_message": 8000,
    "email_subject": 100,
    "twitter_dm": 10000,
}

# Common overused phrases to detect
OVERUSED_PHRASES = [
    "i hope this message finds you well",
    "i hope this email finds you well",
    "i am reaching out",
    "i am writing to",
    "i wanted to reach out",
    "i came across your profile",
    "i noticed your profile",
    "i would love to connect",
    "pick your brain",
    "synergy",
    "circle back",
    "touch base",
    "leverage",
    "low-hanging fruit",
]

# Stronger alternatives for weak phrases
PHRASE_IMPROVEMENTS = {
    "i am reaching out": ["I noticed", "I saw that", "After reviewing"],
    "i hope this finds you well": ["", "I hope you're having a great week"],
    "pick your brain": ["learn from your experience", "get your perspective", "hear your thoughts"],
    "touch base": ["connect", "follow up", "check in"],
    "leverage": ["use", "apply", "utilize"],
}


def generate_message(
    template: MessageTemplate,
    contact: Contact,
    user_profile: UserProfile
) -> str:
    """
    Generate a personalized message by filling in template placeholders.

    Available placeholders:
    - {name} - Contact's first name
    - {full_name} - Contact's full name
    - {company} - Contact's company
    - {role} - Contact's job title
    - {school} - Shared school (if alumni)
    - {my_name} - Your name
    - {my_title} - Your current title
    - {my_background} - Your elevator pitch
    - {my_skills} - Your key skills
    """
    message = template.template

    # Contact info
    first_name = contact.name.split()[0] if contact.name else "there"
    message = message.replace("{name}", first_name)
    message = message.replace("{full_name}", contact.name or "")
    message = message.replace("{company}", contact.company or "your company")
    message = message.replace("{role}", contact.role or "your role")

    # Alumni connection
    if contact.is_alumni and contact.school_name:
        message = message.replace("{school}", contact.school_name)
    elif user_profile.school:
        message = message.replace("{school}", user_profile.school)
    else:
        message = message.replace("{school}", "our school")

    # User info
    message = message.replace("{my_name}", user_profile.name or "")
    message = message.replace("{my_title}", user_profile.current_title or "software developer")
    message = message.replace("{my_background}", user_profile.elevator_pitch or "")
    message = message.replace("{my_skills}", user_profile.skills or "")

    # Clean up any unfilled placeholders
    message = re.sub(r'\{[^}]+\}', '', message)

    return message.strip()


def validate_message_length(message: str, platform: str = "linkedin_connection") -> Dict:
    """
    Validate message length for different platforms.

    Args:
        message: The message text
        platform: One of 'linkedin_connection', 'linkedin_inmail', 'linkedin_message',
                 'email_subject', 'twitter_dm'

    Returns:
        {
            "valid": True/False,
            "length": 250,
            "limit": 300,
            "remaining": 50,
            "platform": "linkedin_connection"
        }
    """
    limit = PLATFORM_LIMITS.get(platform, 1000)
    length = len(message)

    return {
        "valid": length <= limit,
        "length": length,
        "limit": limit,
        "remaining": limit - length,
        "platform": platform,
        "message": f"{'OK' if length <= limit else f'Too long by {length - limit} characters'}"
    }


def detect_overused_phrases(message: str) -> List[Dict]:
    """
    Detect overused phrases in a message.

    Returns:
        [
            {
                "phrase": "I hope this finds you well",
                "suggestion": "Consider removing or replacing with something more specific"
            }
        ]
    """
    found = []
    message_lower = message.lower()

    for phrase in OVERUSED_PHRASES:
        if phrase in message_lower:
            suggestions = PHRASE_IMPROVEMENTS.get(phrase, ["Consider rephrasing for originality"])
            found.append({
                "phrase": phrase,
                "suggestion": f"Try: {suggestions[0]}" if suggestions[0] else "Consider removing this phrase"
            })

    return found


def suggest_message_improvements(message: str) -> List[str]:
    """
    Analyze a message and suggest improvements.

    Returns list of improvement suggestions.
    """
    suggestions = []

    # Check for overused phrases
    overused = detect_overused_phrases(message)
    if overused:
        suggestions.append(f"Found {len(overused)} overused phrase(s) - consider rephrasing for originality")

    # Check message length
    if len(message) < 50:
        suggestions.append("Message seems too short - add more personalization")
    elif len(message) > 300 and "linkedin" in message.lower():
        suggestions.append("Message may be too long for LinkedIn connection request (300 char limit)")

    # Check for personalization
    generic_signs = ["[", "]", "specific reason", "company name here"]
    for sign in generic_signs:
        if sign.lower() in message.lower():
            suggestions.append(f"Replace placeholder '{sign}' with specific information")

    # Check for call to action
    cta_phrases = ["chat", "call", "meet", "connect", "discuss", "talk", "coffee", "?"]
    if not any(phrase in message.lower() for phrase in cta_phrases):
        suggestions.append("Consider adding a clear call-to-action (e.g., 'Would you be open to a quick chat?')")

    # Check for self-focus vs other-focus
    i_count = len(re.findall(r'\bI\b', message))
    you_count = len(re.findall(r'\byou\b', message, re.IGNORECASE))
    if i_count > you_count * 2:
        suggestions.append("Message may be too self-focused - try to focus more on the recipient")

    # Check for specific details
    if not re.search(r'\b(at|@)\s*\w+', message) and "{company}" not in message:
        suggestions.append("Add specific details about the recipient's company or work")

    return suggestions


def generate_variations(
    template: MessageTemplate,
    contact: Contact,
    user_profile: UserProfile,
    count: int = 3
) -> List[Dict]:
    """
    Generate multiple variations of a message for A/B testing.

    Returns:
        [
            {"variation": "A", "message": "...", "character_count": 245},
            {"variation": "B", "message": "...", "character_count": 280},
        ]
    """
    base_message = generate_message(template, contact, user_profile)
    variations = [{"variation": "A", "message": base_message, "character_count": len(base_message)}]

    # Generate variations by tweaking the message
    variation_strategies = [
        _vary_greeting,
        _vary_closing,
        _vary_cta,
    ]

    for i, strategy in enumerate(variation_strategies[:count-1]):
        varied = strategy(base_message, contact)
        variations.append({
            "variation": chr(66 + i),  # B, C, D, etc.
            "message": varied,
            "character_count": len(varied)
        })

    return variations


def _vary_greeting(message: str, contact: Contact) -> str:
    """Vary the greeting of a message."""
    greetings = [
        f"Hi {contact.name.split()[0] if contact.name else 'there'}",
        f"Hello {contact.name.split()[0] if contact.name else 'there'}",
        f"Hey {contact.name.split()[0] if contact.name else 'there'}",
    ]

    # Find and replace first greeting
    patterns = [r'^Hi \w+', r'^Hello \w+', r'^Hey \w+', r'^Dear \w+']
    for pattern in patterns:
        if re.match(pattern, message):
            return re.sub(pattern, random.choice(greetings), message)

    return message


def _vary_closing(message: str, contact: Contact) -> str:
    """Vary the closing of a message."""
    closings = [
        "Best regards,",
        "Best,",
        "Thanks,",
        "Cheers,",
        "Looking forward to connecting,",
    ]

    # Find and replace closing
    patterns = [r'Best regards,', r'Best,', r'Thanks,', r'Cheers,', r'Sincerely,']
    for pattern in patterns:
        if pattern in message:
            return message.replace(pattern, random.choice(closings))

    return message


def _vary_cta(message: str, contact: Contact) -> str:
    """Vary the call-to-action."""
    ctas = [
        "Would you be open to a quick chat?",
        "Would love to hear your thoughts sometime.",
        "I'd appreciate any insights you could share.",
        "Would a brief call work for you?",
        "Happy to chat whenever works for you.",
    ]

    # Try to find and replace existing CTA
    cta_patterns = [
        r"Would you be open to .*?\?",
        r"Would love to .*?\.",
        r"Would you have .*?\?",
        r"I'd love to .*?\.",
    ]

    for pattern in cta_patterns:
        if re.search(pattern, message):
            return re.sub(pattern, random.choice(ctas), message)

    return message


def generate_followup_sequence(
    contact: Contact,
    user_profile: UserProfile,
    context: str = "general"
) -> List[Dict]:
    """
    Generate a sequence of follow-up messages (day 3, day 7, day 14).

    Args:
        contact: The contact to follow up with
        user_profile: User's profile
        context: 'general', 'application', 'meeting', 'referral'

    Returns:
        [
            {"day": 3, "subject": "...", "message": "..."},
            {"day": 7, "subject": "...", "message": "..."},
            {"day": 14, "subject": "...", "message": "..."}
        ]
    """
    first_name = contact.name.split()[0] if contact.name else "there"
    company = contact.company or "your company"
    my_name = user_profile.name or ""

    sequences = {
        "general": [
            {
                "day": 3,
                "subject": f"Following up - {my_name}",
                "message": f"""Hi {first_name},

I wanted to follow up on my previous message. I know you're busy, so I'll keep this brief.

I'm still very interested in connecting and learning more about your experience at {company}. Would you have 10-15 minutes for a quick call this week?

Thanks,
{my_name}"""
            },
            {
                "day": 7,
                "subject": f"Quick check-in",
                "message": f"""Hi {first_name},

I hope this message finds you well. I wanted to reach out one more time in case my previous messages got lost in the shuffle.

I'd genuinely value the opportunity to connect with you, even if just for a brief conversation. If you're too busy right now, I completely understand - perhaps we could connect later?

Best,
{my_name}"""
            },
            {
                "day": 14,
                "subject": f"Last follow-up from {my_name}",
                "message": f"""Hi {first_name},

This will be my last follow-up - I don't want to clutter your inbox!

If you're ever open to connecting in the future, I'd still love to chat. Feel free to reach out whenever works for you.

Wishing you all the best,
{my_name}"""
            }
        ],
        "application": [
            {
                "day": 3,
                "subject": f"Following up on my application",
                "message": f"""Hi {first_name},

I wanted to follow up on my application for the position at {company}. I remain very excited about this opportunity and would welcome the chance to discuss how I can contribute to your team.

Is there any additional information I can provide?

Best regards,
{my_name}"""
            },
            {
                "day": 7,
                "subject": f"Checking in - {company} application",
                "message": f"""Hi {first_name},

I hope you're doing well! I wanted to check in on the status of my application at {company}.

I'm still very interested in the role and confident I could make a meaningful contribution. If there's anything I can do to support my application, please let me know.

Thanks for your time,
{my_name}"""
            },
            {
                "day": 14,
                "subject": f"Final follow-up - {company}",
                "message": f"""Hi {first_name},

I wanted to send one final follow-up regarding my application at {company}. I understand you likely have many candidates to review, so I appreciate your time.

If the role has been filled or if you've decided to move forward with other candidates, I would appreciate a brief update so I can adjust my job search accordingly.

Thank you for your consideration,
{my_name}"""
            }
        ],
        "meeting": [
            {
                "day": 3,
                "subject": f"Great speaking with you!",
                "message": f"""Hi {first_name},

Thank you again for taking the time to speak with me! I really enjoyed our conversation and learning more about {company}.

I've been thinking about what we discussed, particularly [specific point]. I'd love to continue the conversation if you're open to it.

Best,
{my_name}"""
            },
            {
                "day": 7,
                "subject": f"Following up on our conversation",
                "message": f"""Hi {first_name},

I wanted to follow up on our conversation from last week. I hope things are going well at {company}.

If there's anything I can help with or if you'd like to continue our discussion, I'm happy to connect again.

Thanks,
{my_name}"""
            },
            {
                "day": 14,
                "subject": f"Staying in touch",
                "message": f"""Hi {first_name},

I wanted to stay in touch after our conversation. I'm continuing to explore opportunities in the space and would love to keep you updated on my progress.

Feel free to reach out anytime - I'm always happy to connect.

Best regards,
{my_name}"""
            }
        ],
        "referral": [
            {
                "day": 3,
                "subject": f"Thank you for the referral!",
                "message": f"""Hi {first_name},

Thank you so much for referring me to the role at {company}! I really appreciate you taking the time to help me out.

I submitted my application and wanted to let you know. Is there anything else you'd recommend I do to strengthen my candidacy?

Thanks again,
{my_name}"""
            },
            {
                "day": 7,
                "subject": f"Update on the {company} application",
                "message": f"""Hi {first_name},

I wanted to give you a quick update on the application you helped me with. [Status update here]

Thank you again for the referral - I really appreciate your support.

Best,
{my_name}"""
            },
            {
                "day": 14,
                "subject": f"Quick update",
                "message": f"""Hi {first_name},

Just wanted to keep you in the loop on the {company} opportunity. [Status update]

Regardless of how this turns out, I'm grateful for your help and would love to stay in touch.

Best,
{my_name}"""
            }
        ]
    }

    return sequences.get(context, sequences["general"])


def get_default_templates() -> list:
    """
    Return default message templates to seed the database.
    """
    return [
        # Connection requests (short - LinkedIn limit is 300 chars)
        {
            "name": "Alumni Connection Request",
            "message_type": "connection_request",
            "target_type": "alumni",
            "template": "Hi {name}, I noticed we both went to {school}! I'm currently exploring opportunities in software development and would love to connect with fellow alumni. Would be great to be in touch!",
            "is_default": True
        },
        {
            "name": "Recruiter Connection Request",
            "message_type": "connection_request",
            "target_type": "recruiter",
            "template": "Hi {name}, I came across your profile and see you recruit for tech roles at {company}. I'm a software developer actively exploring new opportunities and would love to connect!",
            "is_default": True
        },
        {
            "name": "Developer Connection Request",
            "message_type": "connection_request",
            "target_type": "developer",
            "template": "Hi {name}, I saw you work as a {role} at {company}. I'm also in software development and always looking to connect with others in the field. Would love to be in touch!",
            "is_default": True
        },
        {
            "name": "General Connection Request",
            "message_type": "connection_request",
            "target_type": "general",
            "template": "Hi {name}, I came across your profile and would love to connect. I'm a software developer exploring new opportunities. Looking forward to being in touch!",
            "is_default": True
        },

        # InMails / longer messages
        {
            "name": "Alumni InMail",
            "message_type": "inmail",
            "target_type": "alumni",
            "subject": "Fellow {school} alum - quick question",
            "template": """Hi {name},

I hope this message finds you well! I noticed we're both {school} alumni, and I wanted to reach out.

I'm currently a {my_title} with experience in {my_skills}, and I'm exploring new opportunities in software development. I've been really impressed by the work {company} is doing.

Would you have 15-20 minutes for a quick call? I'd love to hear about your experience at {company} and any advice you might have for someone looking to make a move in the industry.

Thanks so much for considering!

Best,
{my_name}""",
            "is_default": True
        },
        {
            "name": "Recruiter InMail",
            "message_type": "inmail",
            "target_type": "recruiter",
            "subject": "Software Developer - Interested in {company}",
            "template": """Hi {name},

I came across your profile and wanted to reach out about opportunities at {company}.

{my_background}

I'm particularly interested in {company} because of [specific reason]. I'd love to learn more about any software development roles you might be hiring for.

Would you have a few minutes to chat? I'm happy to send over my resume if helpful.

Best regards,
{my_name}""",
            "is_default": True
        },

        # Follow-ups
        {
            "name": "Connection Follow-up",
            "message_type": "follow_up",
            "target_type": "general",
            "template": """Hi {name},

Thanks for connecting! I wanted to follow up and introduce myself properly.

{my_background}

I'd love to hear more about your work at {company}. Would you be open to a quick chat sometime?

Best,
{my_name}""",
            "is_default": True
        },
        {
            "name": "Application Follow-up",
            "message_type": "follow_up",
            "target_type": "recruiter",
            "template": """Hi {name},

I wanted to follow up on my application for the [role] position at {company} that I submitted [timeframe] ago.

I'm very excited about this opportunity and believe my experience in {my_skills} would be a great fit for the team.

Is there any additional information I can provide to support my application?

Thank you for your time!

Best,
{my_name}""",
            "is_default": True
        },

        # Thank you messages
        {
            "name": "Interview Thank You",
            "message_type": "thank_you",
            "target_type": "general",
            "template": """Hi {name},

Thank you so much for taking the time to speak with me today about the [role] position at {company}.

I really enjoyed learning more about [specific topic discussed] and am even more excited about the opportunity to contribute to the team.

Please don't hesitate to reach out if you need any additional information from me.

Best regards,
{my_name}""",
            "is_default": True
        }
    ]
