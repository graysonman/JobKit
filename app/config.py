"""
JobKit - Application configuration.

Centralized configuration using Pydantic Settings for environment variable management.

Environment Variables:
    All settings can be overridden via environment variables with JOBKIT_ prefix.

    AI Settings:
        JOBKIT_AI_ENABLED=true           - Toggle AI features
        JOBKIT_GROQ_API_KEY=...          - Groq API key from console.groq.com
        JOBKIT_GROQ_MODEL=...            - Model to use (e.g., llama-3.3-70b-versatile)

    Auth Settings:
        JOBKIT_SINGLE_USER_MODE=true     - Skip auth for local use
        JOBKIT_SECRET_KEY=...            - JWT signing key (required in production)
"""
from pydantic_settings import BaseSettings
from typing import Optional


class AISettings(BaseSettings):
    """
    AI/Groq API configuration settings.

    Available models (as of 2024):
        - llama-3.3-70b-versatile: Best quality, 128k context
        - llama-3.1-8b-instant: Fastest, good for simple tasks
        - mixtral-8x7b-32768: Good balance of speed/quality
        - gemma2-9b-it: Google's Gemma 2, instruction-tuned
    """
    ai_enabled: bool = True
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1024
    ai_fallback_to_template: bool = True

    class Config:
        env_prefix = "JOBKIT_"
        env_file = ".env"
        extra = "ignore"


class AuthSettings(BaseSettings):
    """
    Authentication configuration settings.

    For production deployment:
        1. Set JOBKIT_SINGLE_USER_MODE=false
        2. Generate a secret key: openssl rand -hex 32
        3. Set JOBKIT_SECRET_KEY to the generated key
        4. Optionally configure OAuth providers
    """
    single_user_mode: bool = True
    secret_key: str = "development-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OAuth2 providers
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None

    class Config:
        env_prefix = "JOBKIT_"
        env_file = ".env"
        extra = "ignore"


class Settings(BaseSettings):
    """Combined application settings."""
    ai: AISettings = AISettings()
    auth: AuthSettings = AuthSettings()

    # CORS allowed origins (comma-separated, e.g. "http://localhost:3000,https://myapp.com")
    allowed_origins: str = "*"

    # Database
    database_url: str = "sqlite:///./data/jobkit.db"

    # Database connection pool (PostgreSQL only)
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # Database retry settings
    db_retry_max_attempts: int = 3
    db_retry_base_delay: float = 0.1

    class Config:
        env_prefix = "JOBKIT_"
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()
