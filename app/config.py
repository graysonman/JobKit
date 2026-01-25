"""
JobKit - Application configuration.

Centralized configuration using Pydantic Settings for environment variable management.

Environment Variables:
    All settings can be overridden via environment variables with JOBKIT_ prefix.

    AI Settings:
        JOBKIT_AI_ENABLED=true           - Toggle AI features
        JOBKIT_OLLAMA_BASE_URL=...       - Ollama server URL
        JOBKIT_OLLAMA_MODEL=...          - Model to use

    Auth Settings:
        JOBKIT_SINGLE_USER_MODE=true     - Skip auth for local use
        JOBKIT_SECRET_KEY=...            - JWT signing key (required in production)
"""
from pydantic_settings import BaseSettings
from typing import Optional


class AISettings(BaseSettings):
    """
    AI/Ollama configuration settings.

    Recommended models by hardware:
        - 8GB+ RAM + GPU: mistral:7b-instruct (4.1GB)
        - 8GB+ RAM, CPU-only: phi3:mini (2.3GB)
        - 4-8GB RAM: phi3:mini or qwen2:1.5b (1-2GB)
    """
    ai_enabled: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 1024
    ai_fallback_to_template: bool = True

    class Config:
        env_prefix = "JOBKIT_"
        env_file = ".env"


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


class Settings(BaseSettings):
    """Combined application settings."""
    ai: AISettings = AISettings()
    auth: AuthSettings = AuthSettings()

    # Database
    database_url: str = "sqlite:///./data/jobkit.db"

    class Config:
        env_prefix = "JOBKIT_"
        env_file = ".env"


# Global settings instance
settings = Settings()
