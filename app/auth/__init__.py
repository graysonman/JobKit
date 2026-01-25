"""
JobKit - Authentication Module

Multi-user authentication with JWT and OAuth2 support.

Usage:
    from app.auth import get_current_user, get_current_active_user
    from app.auth import auth_service, User

    @router.get("/protected")
    def protected_route(current_user: User = Depends(get_current_active_user)):
        return {"user_id": current_user.id}

Configuration (environment variables):
    JOBKIT_SINGLE_USER_MODE=true     - Skip auth for local single-user mode
    JOBKIT_SECRET_KEY=<key>          - JWT signing key (required in production)
    JOBKIT_ACCESS_TOKEN_EXPIRE_MINUTES=30
    JOBKIT_REFRESH_TOKEN_EXPIRE_DAYS=7
"""

# Models
from .models import User, OAuthAccount, RefreshToken

# Service
from .service import auth_service, AuthServiceError

# Dependencies (for use in routers)
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_verified_user,
    get_current_user_optional,
    get_user_id,
    is_single_user_mode,
    require_auth_available,
)

# Router (for mounting in main.py)
from .router import router

__all__ = [
    # Models
    "User",
    "OAuthAccount",
    "RefreshToken",
    # Service
    "auth_service",
    "AuthServiceError",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "get_current_user_optional",
    "get_user_id",
    "is_single_user_mode",
    "require_auth_available",
    # Router
    "router",
]
