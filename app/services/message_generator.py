"""
JobKit - Message generation service.

Creates personalized outreach messages for networking contacts
using templates with placeholder substitution.
"""
from ..models import MessageTemplate, Contact, UserProfile
from typing import Optional, List
import re

# TODO: Add OpenAI integration for AI-powered message generation
# TODO: Add message length validation (LinkedIn connection request = 300 chars)
# TODO: Add A/B testing support for template variations
# TODO: Add sentiment analysis for generated messages

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

    # TODO Phase 3: Add smarter placeholder handling
    # TODO Phase 3: Add variation generation (multiple versions)
    # TODO Phase 5: Add AI-powered personalization using OpenAI

    return message.strip()


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


# TODO: Add function to analyze which templates get best response rates
# TODO: Add function to generate multiple message variations for A/B testing
# TODO: Add function to validate message length for different platforms (LinkedIn, email, etc.)
# TODO: Add AI message generation function using OpenAI
# def generate_ai_message(contact: Contact, user_profile: UserProfile, context: str) -> str:
#     """Use OpenAI to generate a highly personalized message."""
#     pass

# TODO: Add function to detect and warn about overused phrases
# TODO: Add function to suggest improvements to user-written messages
# TODO: Add function to generate follow-up sequence (day 3, day 7, day 14 messages)
