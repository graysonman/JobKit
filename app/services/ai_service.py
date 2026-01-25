"""
JobKit - AI Service (Ollama Integration)

Abstraction layer for local AI model inference using Ollama.

Setup:
1. Install Ollama: https://ollama.ai/download
2. Start Ollama: ollama serve
3. Pull a model: ollama pull mistral:7b-instruct (or phi3:mini for lower RAM)
4. The service will auto-detect availability

This service provides:
- AI availability checking
- Model listing for UI selection
- Cover letter generation with AI
- Semantic skill extraction
- Message generation with AI
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
    AI Service for local LLM inference via Ollama.

    Provides AI-powered text generation with graceful fallback
    when Ollama is not available.
    """

    def __init__(self):
        """Initialize AI service with settings."""
        self.base_url = settings.ai.ollama_base_url
        self.model = settings.ai.ollama_model
        self.enabled = settings.ai.ai_enabled
        self.temperature = settings.ai.ai_temperature
        self.max_tokens = settings.ai.ai_max_tokens
        self._availability_cache: Optional[bool] = None
        self._models_cache: Optional[List[str]] = None

    def _check_httpx(self) -> None:
        """Check if httpx is available."""
        if not HTTPX_AVAILABLE:
            raise AIServiceError(
                "httpx is required for AI features. Install with: pip install httpx"
            )

    async def is_available(self) -> bool:
        """
        Check if Ollama is running and accessible.

        Returns True if:
        - AI is enabled in settings
        - httpx is installed
        - Ollama server responds to health check

        Results are cached for performance.
        """
        if not self.enabled:
            logger.debug("AI is disabled in settings")
            return False

        if not HTTPX_AVAILABLE:
            logger.warning("httpx not installed - AI features unavailable")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                available = response.status_code == 200
                if available:
                    logger.debug(f"Ollama is available at {self.base_url}")
                else:
                    logger.warning(f"Ollama returned status {response.status_code}")
                return available
        except httpx.ConnectError:
            logger.info("Ollama is not running or not accessible")
            return False
        except httpx.TimeoutException:
            logger.warning("Ollama connection timed out")
            return False
        except Exception as e:
            logger.warning(f"Ollama availability check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """
        List available Ollama models for UI model selector.

        Returns:
            List of model names (e.g., ["mistral:7b-instruct", "phi3:mini"])
            Empty list if Ollama is unavailable
        """
        if not await self.is_available():
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=10.0
                )
                if response.status_code != 200:
                    return []

                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                logger.debug(f"Found {len(models)} Ollama models")
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

        if not await self.is_available():
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/show",
                    json={"name": model},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None

    async def _generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Internal method to call Ollama generate API.

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

        if not await self.is_available():
            raise AIServiceError("Ollama is not available")

        request_body: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens
            }
        }

        if system_prompt:
            request_body["system"] = system_prompt

        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Generating with model {self.model}")
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=request_body,
                    timeout=120.0  # LLM generation can take time
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Ollama error: {error_text}")
                    raise AIServiceError(f"Ollama returned status {response.status_code}")

                data = response.json()
                result = data.get("response", "")

                logger.debug(f"Generated {len(result)} characters")
                return result.strip()

        except httpx.TimeoutException:
            logger.error("AI generation timed out")
            raise AIServiceError("AI generation timed out - try a smaller model")
        except httpx.ConnectError:
            logger.error("Lost connection to Ollama")
            raise AIServiceError("Lost connection to Ollama")
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
        length: str = "medium"
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

        Returns:
            Tuple[str, bool]: (cover_letter_text, was_ai_generated)
        """
        from .ai_prompts import COVER_LETTER_PROMPT

        prompt = COVER_LETTER_PROMPT.format(
            name=profile.get("name", ""),
            current_title=profile.get("current_title", "Software Developer"),
            skills=profile.get("skills", ""),
            years_experience=profile.get("years_experience", ""),
            elevator_pitch=profile.get("elevator_pitch", ""),
            job_description=job_description[:3000],  # Limit job description length
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

        return text.strip()

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
        from .ai_prompts import SKILL_EXTRACTION_PROMPT

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
        from .ai_prompts import MESSAGE_GENERATION_PROMPT

        # Get platform character limits
        max_chars = {
            "connection_request": 300,
            "inmail": 1900,
            "follow_up": 1000,
            "thank_you": 800,
            "cold_email": 1500
        }.get(message_type, 1000)

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
            r"^\*\*.*?\*\*\s*",  # Bold headers
        ]
        for pattern in preambles:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        text = text.strip()

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
        from .ai_prompts import JOB_ANALYSIS_PROMPT

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
        from .ai_prompts import RESUME_TAILORING_PROMPT

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
