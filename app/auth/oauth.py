"""
JobKit - OAuth2 Provider Configuration

Configuration for OAuth2 providers (Google, GitHub).

# =============================================================================
# TODO: Multi-User Authentication (Feature 2) - Implement OAuth2 providers
# =============================================================================

Dependencies:
    pip install authlib httpx

Setup:
    1. Google OAuth:
       - Go to https://console.cloud.google.com/apis/credentials
       - Create OAuth 2.0 Client ID
       - Set authorized redirect URI: {YOUR_URL}/auth/oauth/google/callback
       - Set JOBKIT_GOOGLE_CLIENT_ID and JOBKIT_GOOGLE_CLIENT_SECRET in .env

    2. GitHub OAuth:
       - Go to https://github.com/settings/developers
       - Create new OAuth App
       - Set callback URL: {YOUR_URL}/auth/oauth/github/callback
       - Set JOBKIT_GITHUB_CLIENT_ID and JOBKIT_GITHUB_CLIENT_SECRET in .env
"""
from typing import Dict, Optional

# TODO: Uncomment when implementing
# from authlib.integrations.starlette_client import OAuth

from ..config import settings


# OAuth client configuration
# TODO: Uncomment and configure when implementing
"""
oauth = OAuth()

# Google OAuth2 configuration
if settings.auth.google_client_id:
    oauth.register(
        name="google",
        client_id=settings.auth.google_client_id,
        client_secret=settings.auth.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        }
    )

# GitHub OAuth2 configuration
if settings.auth.github_client_id:
    oauth.register(
        name="github",
        client_id=settings.auth.github_client_id,
        client_secret=settings.auth.github_client_secret,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        client_kwargs={
            "scope": "user:email"
        }
    )

# Export configured OAuth clients
oauth_clients: Dict[str, object] = {}

if settings.auth.google_client_id:
    oauth_clients["google"] = oauth.google

if settings.auth.github_client_id:
    oauth_clients["github"] = oauth.github
"""


# Placeholder until OAuth is implemented
oauth_clients: Dict[str, object] = {}


def get_oauth_client(provider: str) -> Optional[object]:
    """
    Get the OAuth client for a provider.

    Args:
        provider: OAuth provider name ("google" or "github")

    Returns:
        OAuth client instance or None if not configured

    TODO: Implement:
        return oauth_clients.get(provider)
    """
    return oauth_clients.get(provider)


def is_oauth_configured(provider: str) -> bool:
    """
    Check if an OAuth provider is configured.

    TODO: Implement:
        return provider in oauth_clients
    """
    return provider in oauth_clients


def list_configured_providers() -> list:
    """
    List all configured OAuth providers.

    TODO: Implement:
        return list(oauth_clients.keys())
    """
    return list(oauth_clients.keys())


# OAuth user info extraction helpers
def extract_google_user_info(token_data: dict) -> dict:
    """
    Extract user info from Google OAuth response.

    TODO: Implement:
        return {
            "email": token_data.get("email"),
            "name": token_data.get("name"),
            "picture": token_data.get("picture"),
            "provider_user_id": token_data.get("sub")
        }
    """
    return {
        "email": token_data.get("email"),
        "name": token_data.get("name"),
        "picture": token_data.get("picture"),
        "provider_user_id": token_data.get("sub")
    }


def extract_github_user_info(user_data: dict, emails_data: list) -> dict:
    """
    Extract user info from GitHub OAuth response.

    Note: GitHub requires separate API call for email if not public.

    TODO: Implement:
        # Find primary email
        primary_email = None
        for email in emails_data:
            if email.get("primary") and email.get("verified"):
                primary_email = email.get("email")
                break

        return {
            "email": primary_email or user_data.get("email"),
            "name": user_data.get("name") or user_data.get("login"),
            "picture": user_data.get("avatar_url"),
            "provider_user_id": str(user_data.get("id"))
        }
    """
    primary_email = None
    for email in emails_data:
        if email.get("primary") and email.get("verified"):
            primary_email = email.get("email")
            break

    return {
        "email": primary_email or user_data.get("email"),
        "name": user_data.get("name") or user_data.get("login"),
        "picture": user_data.get("avatar_url"),
        "provider_user_id": str(user_data.get("id"))
    }
