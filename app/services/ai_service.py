"""
JobKit - AI Service (Groq API Integration)

Abstraction layer for AI inference using Groq's ultra-fast LPU cloud.

Setup:
1. Get an API key from https://console.groq.com/
2. Set JOBKIT_GROQ_API_KEY in your .env file
3. The service will auto-detect availability

This service provides:
- AI availability checking
- Cover letter generation with AI
- Semantic skill extraction
- Message generation with AI
- Job description analysis
- Resume tailoring suggestions
- Graceful fallback when AI unavailable
"""
from typing import List, Dict, Tuple, Optional, Any
import logging
import json
import re

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from ..config import settings

logger = logging.getLogger("jobkit.ai")


class AIServiceError(Exception):
    """Custom exception for AI service errors."""
    pass


class AIService:
    """
    AI Service for LLM inference via Groq API.

    Provides AI-powered text generation with graceful fallback
    when the API is not available.
    """

    def __init__(self):
        """Initialize AI service with settings."""
        self.base_url = settings.ai.groq_base_url
        self.api_key = settings.ai.groq_api_key
        self.model = settings.ai.groq_model
        self.enabled = settings.ai.ai_enabled
        self.temperature = settings.ai.ai_temperature
        self.max_tokens = settings.ai.ai_max_tokens
        self._availability_cache: Optional[bool] = None

    def _check_httpx(self) -> None:
        """Check if httpx is available."""
        if not HTTPX_AVAILABLE:
            raise AIServiceError(
                "httpx is required for AI features. Install with: pip install httpx"
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Groq API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def is_available(self) -> bool:
        """
        Check if Groq API is accessible.

        Returns True if:
        - AI is enabled in settings
        - API key is configured
        - httpx is installed
        - Groq API responds successfully

        Results are cached for performance.
        """
        if not self.enabled:
            logger.debug("AI is disabled in settings")
            return False

        if not self.api_key:
            logger.warning("Groq API key not configured - AI features unavailable")
            return False

        if not HTTPX_AVAILABLE:
            logger.warning("httpx not installed - AI features unavailable")
            return False

        try:
            async with httpx.AsyncClient() as client:
                # Use the models endpoint as a health check
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                available = response.status_code == 200
                if available:
                    logger.debug("Groq API is available")
                else:
                    logger.warning(f"Groq API returned status {response.status_code}")
                return available
        except httpx.ConnectError:
            logger.info("Groq API is not accessible")
            return False
        except httpx.TimeoutException:
            logger.warning("Groq API connection timed out")
            return False
        except Exception as e:
            logger.warning(f"Groq API availability check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """
        List available Groq models for UI model selector.

        Returns:
            List of model names (e.g., ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"])
            Empty list if API is unavailable
        """
        if not await self.is_available():
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                if response.status_code != 200:
                    return []

                data = response.json()
                models = [model["id"] for model in data.get("data", [])]
                logger.debug(f"Found {len(models)} Groq models")
                return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def get_model_info(self, model_name: Optional[str] = None) -> Optional[Dict]:
        """
        Get information about a specific model.

        Args:
            model_name: Model name (defaults to configured model)

        Returns:
            Model info dict or None if not found
        """
        model = model_name or self.model
        models = await self.list_models()

        if model in models:
            return {"id": model, "available": True}
        return None

    async def _generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Internal method to call Groq chat completions API.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Generated text response

        Raises:
            AIServiceError: If generation fails
        """
        self._check_httpx()

        if not self.api_key:
            raise AIServiceError("Groq API key not configured")

        if not await self.is_available():
            raise AIServiceError("Groq API is not available")

        # Build messages array (OpenAI-compatible format)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False
        }

        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Generating with model {self.model}")
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=request_body,
                    timeout=120.0  # LLM generation can take time
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Groq API error: {error_text}")
                    raise AIServiceError(f"Groq API returned status {response.status_code}")

                data = response.json()

                # Extract content from OpenAI-compatible response format
                choices = data.get("choices", [])
                if not choices:
                    raise AIServiceError("No response generated")

                result = choices[0].get("message", {}).get("content", "")

                logger.debug(f"Generated {len(result)} characters")
                return result.strip()

        except httpx.TimeoutException:
            logger.error("AI generation timed out")
            raise AIServiceError("AI generation timed out")
        except httpx.ConnectError:
            logger.error("Lost connection to Groq API")
            raise AIServiceError("Lost connection to Groq API")
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            raise AIServiceError(f"AI generation failed: {str(e)}")

    async def generate_cover_letter_ai(
        self,
        profile: Dict,
        job_description: str,
        company_name: str,
        role: str,
        tone: str = "professional",
        length: str = "medium",
        resume_text: str = ""
    ) -> Tuple[str, bool]:
        """
        Generate a cover letter using AI.

        Args:
            profile: User profile dict with name, skills, experience, etc.
            job_description: Full job posting text
            company_name: Target company name
            role: Job title/role
            tone: Writing tone (professional, conversational, enthusiastic, formal)
            length: Desired length (short ~150 words, medium ~250, detailed ~350)
            resume_text: Full resume text for context

        Returns:
            Tuple[str, bool]: (cover_letter_text, was_ai_generated)
        """
        from .ai_prompts import ALL_PROMPTS as _prompts; COVER_LETTER_PROMPT = _prompts["cover_letter"]

        prompt = COVER_LETTER_PROMPT.format(
            name=profile.get("name", ""),
            current_title=profile.get("current_title", "Software Developer"),
            skills=profile.get("skills", ""),
            years_experience=profile.get("years_experience", ""),
            elevator_pitch=profile.get("elevator_pitch", ""),
            resume_text=resume_text[:3000] if resume_text else "Not provided",
            job_description=job_description[:3000],
            company_name=company_name,
            role=role,
            tone=tone,
            length=length
        )

        # Adjust max tokens based on length
        max_tokens = {
            "short": 400,
            "medium": 600,
            "detailed": 900
        }.get(length, 600)

        response = await self._generate(prompt, max_tokens=max_tokens)

        # Clean up the response - remove any meta-commentary
        response = self._clean_cover_letter(response, profile.get("name", ""))

        return response, True

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace and strip markdown artifacts from AI output."""
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove markdown bold/italic markers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold** → bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)       # *italic* → italic
        text = re.sub(r'__(.+?)__', r'\1', text)        # __bold__ → bold
        text = re.sub(r'_(.+?)_', r'\1', text)          # _italic_ → italic

        # Remove markdown horizontal rules
        text = re.sub(r'\n-{3,}\n', '\n\n', text)
        text = re.sub(r'\n\*{3,}\n', '\n\n', text)

        # Strip trailing whitespace from each line
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # Collapse 3+ consecutive newlines into 2 (preserve paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _clean_cover_letter(self, text: str, name: str) -> str:
        """Clean up AI-generated cover letter."""
        # Remove common AI preambles
        preambles = [
            r"^(Here'?s?|Below is|I'?ve written|This is) (a |the |your )?cover letter.*?:\s*",
            r"^Sure[,!]?\s*(here'?s?|I'?ll write).*?:\s*",
        ]
        for pattern in preambles:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Ensure it starts with a greeting if it doesn't
        if not text.strip().startswith("Dear"):
            # Try to find where the actual letter starts
            match = re.search(r"(Dear\s+\w+)", text, re.IGNORECASE)
            if match:
                text = text[match.start():]

        return self._normalize_whitespace(text)

    async def extract_skills_semantic(
        self,
        text: str,
        context: str = "resume"
    ) -> List[Dict]:
        """
        Semantically extract and categorize skills from text.

        Args:
            text: Resume text or job description
            context: "resume" or "job" to adjust extraction

        Returns:
            List of dicts: [{"skill": "Python", "category": "languages", "confidence": 0.95}]
        """
        from .ai_prompts import ALL_PROMPTS as _prompts; SKILL_EXTRACTION_PROMPT = _prompts["skill_extraction"]

        prompt = SKILL_EXTRACTION_PROMPT.format(
            text=text[:4000],  # Limit text length
            context=context
        )

        try:
            response = await self._generate(prompt, temperature=0.3)  # Lower temp for structured output
            return self._parse_skills_response(response)
        except AIServiceError:
            logger.warning("AI skill extraction failed, returning empty list")
            return []

    def _parse_skills_response(self, response: str) -> List[Dict]:
        """Parse the JSON response from skill extraction."""
        try:
            # Try to find JSON array in response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                skills = json.loads(json_match.group())
                # Validate structure
                valid_skills = []
                for skill in skills:
                    if isinstance(skill, dict) and "skill" in skill:
                        valid_skills.append({
                            "skill": str(skill.get("skill", "")),
                            "category": str(skill.get("category", "other")),
                            "confidence": float(skill.get("confidence", 0.8))
                        })
                return valid_skills
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse skills JSON: {e}")
        except Exception as e:
            logger.warning(f"Error parsing skills response: {e}")

        return []

    async def generate_message_ai(
        self,
        contact: Any,  # Contact model
        profile: Any,  # UserProfile model
        message_type: str,
        context: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Generate personalized outreach message using AI.

        Args:
            contact: Contact model instance
            profile: UserProfile model instance
            message_type: Type of message (connection_request, inmail, follow_up, etc.)
            context: Optional additional context

        Returns:
            Tuple[str, bool]: (message_text, was_ai_generated)
        """
        from .ai_prompts import ALL_PROMPTS as _prompts; MESSAGE_GENERATION_PROMPT = _prompts["message_generation"]

        # Get platform character limits
        max_chars = {
            "connection_request": 300,
            "inmail": 1900,
            "follow_up": 1000,
            "thank_you": 800,
            "cold_email": 1500,
            "referral_request": 500,
            "informational_interview": 400,
            "recruiter_reply": 600,
            "application_status": 300,
            "rejection_response": 300
        }.get(message_type, 1000)

        # Build resume summary for context
        resume_summary = profile.resume_summary or ""
        if not resume_summary and profile.skills:
            resume_summary = f"Skills: {profile.skills}"

        prompt = MESSAGE_GENERATION_PROMPT.format(
            contact_name=contact.name or "there",
            contact_company=contact.company or "your company",
            contact_role=contact.role or "your role",
            contact_type=contact.contact_type or "professional",
            is_alumni="Yes" if contact.is_alumni else "No",
            school=contact.school_name or profile.school or "",
            my_name=profile.name or "",
            my_title=profile.current_title or "software developer",
            my_skills=profile.skills or "",
            elevator_pitch=profile.elevator_pitch or "",
            resume_summary=resume_summary or "Not provided",
            message_type=message_type,
            context=context or "No additional context"
        )

        # Adjust tokens based on message type
        max_tokens = min(max_chars // 3, 500)  # Rough estimate

        response = await self._generate(prompt, max_tokens=max_tokens)

        # Clean up and enforce character limit
        response = self._clean_message(response, message_type, max_chars)

        return response, True

    def _clean_message(self, text: str, message_type: str, max_chars: int) -> str:
        """Clean up AI-generated message."""
        # Remove common AI preambles
        preambles = [
            r"^(Here'?s?|Below is|I'?ve written).*?:\s*",
            r"^Sure[,!]?\s*.*?:\s*",
            r"^\*\*Subject:?.*?\*\*\s*",  # **Subject: ...** headers
        ]
        for pattern in preambles:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Normalize whitespace and strip markdown
        text = self._normalize_whitespace(text)

        # Enforce character limit for connection requests
        if message_type == "connection_request" and len(text) > max_chars:
            # Try to cut at sentence boundary
            truncated = text[:max_chars]
            last_period = truncated.rfind('.')
            last_exclaim = truncated.rfind('!')
            cut_point = max(last_period, last_exclaim)
            if cut_point > max_chars * 0.6:  # Keep at least 60%
                text = truncated[:cut_point + 1]
            else:
                text = truncated.rsplit(' ', 1)[0] + "..."

        return text.strip()

    async def analyze_job_description(
        self,
        job_description: str
    ) -> Dict:
        """
        Use AI to analyze a job description in depth.

        Args:
            job_description: Full job posting text

        Returns:
            Dict with analysis including skills, culture signals, red flags
        """
        from .ai_prompts import ALL_PROMPTS as _prompts; JOB_ANALYSIS_PROMPT = _prompts["job_analysis"]

        prompt = JOB_ANALYSIS_PROMPT.format(
            job_description=job_description[:4000]
        )

        try:
            response = await self._generate(prompt, temperature=0.3)
            return self._parse_job_analysis(response)
        except AIServiceError:
            logger.warning("AI job analysis failed")
            return {}

    def _parse_job_analysis(self, response: str) -> Dict:
        """Parse the JSON response from job analysis."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse job analysis JSON: {e}")
        except Exception as e:
            logger.warning(f"Error parsing job analysis: {e}")

        return {}

    async def tailor_resume_suggestions(
        self,
        resume_text: str,
        job_description: str
    ) -> Dict:
        """
        Get AI-powered suggestions for tailoring resume to job.

        Args:
            resume_text: Current resume text
            job_description: Target job description

        Returns:
            Dict with match score and specific suggestions
        """
        from .ai_prompts import ALL_PROMPTS as _prompts; RESUME_TAILORING_PROMPT = _prompts["resume_tailoring"]

        prompt = RESUME_TAILORING_PROMPT.format(
            resume_text=resume_text[:3000],
            job_description=job_description[:3000]
        )

        try:
            response = await self._generate(prompt, temperature=0.4, max_tokens=1500)
            result = self._parse_job_analysis(response)  # Same JSON parsing
            return result
        except AIServiceError:
            logger.warning("AI resume tailoring failed")
            return {}


# Global service instance for convenience
ai_service = AIService()


# Convenience functions for common operations
async def check_ai_available() -> bool:
    """Quick check if AI is available."""
    return await ai_service.is_available()


async def get_available_models() -> List[str]:
    """Get list of available AI models."""
    return await ai_service.list_models()
