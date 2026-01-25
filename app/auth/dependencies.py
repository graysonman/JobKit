"""
JobKit - Authentication Dependencies

FastAPI dependencies for route protection and user injection.

Usage in routers:
    from ..auth.dependencies import get_current_user, get_current_active_user

    @router.get("/protected")
    def protected_route(current_user: User = Depends(get_current_active_user)):
        return {"user_id": current_user.id}

Dependency hierarchy:
    get_current_user          - Base: extracts user from token or single-user mode
    get_current_active_user   - Adds: user must be active
    get_current_verified_user - Adds: user must have verified email

For backwards compatibility during migration:
    get_current_user_optional - Returns None instead of raising 401 if not authenticated
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..config import settings
from .models import User
from .service import auth_service

logger = logging.getLogger("jobkit.auth")

# OAuth2 scheme for token extraction from Authorization header
# auto_error=False allows us to handle missing tokens ourselves
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# -----------------------------------------------------------------------------
# Core Authentication Dependencies
# -----------------------------------------------------------------------------

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.

    In single-user mode (default for local installs):
        - Returns a local user without requiring authentication
        - Backwards compatible with existing single-user setup

    In multi-user mode:
        - Requires valid JWT token in Authorization header
        - Token format: "Bearer <token>"

    Args:
        token: JWT token extracted from Authorization header
        db: Database session

    Returns:
        User: The authenticated user

    Raises:
        HTTPException: 401 if not authenticated or token invalid
    """
    # Single-user mode: no authentication required
    if settings.auth.single_user_mode:
        return get_or_create_local_user(db)

    # Multi-user mode: require valid token
    if not token:
        logger.debug("No token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify the token
    token_data = auth_service.verify_access_token(token)
    if not token_data:
        logger.debug("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        logger.warning(f"Token valid but user {token_data.user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current user and verify they are active.

    Use this dependency for most protected routes.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: The authenticated active user

    Raises:
        HTTPException: 403 if user account is deactivated
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user {current_user.id} attempted access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get the current user and verify their email is verified.

    Use this dependency for sensitive operations that require verified email.

    Args:
        current_user: User from get_current_active_user dependency

    Returns:
        User: The authenticated, active, and verified user

    Raises:
        HTTPException: 403 if email is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email."
        )
    return current_user


# -----------------------------------------------------------------------------
# Optional Authentication (for gradual migration)
# -----------------------------------------------------------------------------

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optionally get the current user, returning None if not authenticated.

    Use this for routes that work both with and without authentication,
    showing different content based on auth status.

    Args:
        token: JWT token (may be None)
        db: Database session

    Returns:
        User if authenticated, None otherwise (never raises 401)
    """
    # Single-user mode: always return local user
    if settings.auth.single_user_mode:
        return get_or_create_local_user(db)

    # No token provided
    if not token:
        return None

    # Try to verify token
    token_data = auth_service.verify_access_token(token)
    if not token_data:
        return None

    # Get user
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        return None

    return user


# -----------------------------------------------------------------------------
# Single-User Mode Support
# -----------------------------------------------------------------------------

def get_or_create_local_user(db: Session) -> User:
    """
    Get or create the local single-user mode user.

    This provides backwards compatibility for local installs that don't need auth.
    The local user has a special email that identifies it as the single-user account.

    Args:
        db: Database session

    Returns:
        User: The local user (created if doesn't exist)
    """
    LOCAL_USER_EMAIL = "local@jobkit.local"

    local_user = db.query(User).filter(User.email == LOCAL_USER_EMAIL).first()

    if not local_user:
        logger.info("Creating local single-user mode user")
        local_user = User(
            email=LOCAL_USER_EMAIL,
            name="Local User",
            is_active=True,
            is_verified=True  # No email verification needed for local user
        )
        db.add(local_user)
        db.commit()
        db.refresh(local_user)

    return local_user


def is_single_user_mode() -> bool:
    """
    Check if the application is running in single-user mode.

    Returns:
        True if single-user mode is enabled
    """
    return settings.auth.single_user_mode


# -----------------------------------------------------------------------------
# Utility Dependencies
# -----------------------------------------------------------------------------

async def get_user_id(
    current_user: User = Depends(get_current_active_user)
) -> int:
    """
    Get just the user ID (convenience dependency).

    Useful when you only need the user ID for filtering queries.

    Args:
        current_user: User from get_current_active_user

    Returns:
        int: The user's ID
    """
    return current_user.id


def require_auth_available():
    """
    Dependency that checks if auth dependencies are installed.

    Use this on auth routes to give a helpful error if dependencies are missing.

    Raises:
        HTTPException: 503 if auth dependencies not installed
    """
    if not auth_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not available. Install dependencies: "
                   "pip install python-jose[cryptography] passlib[bcrypt]"
        )


# -----------------------------------------------------------------------------
# Request Context Helpers
# -----------------------------------------------------------------------------

def get_client_ip(request: Request) -> str:
    """
    Get the client's IP address from the request.

    Handles X-Forwarded-For header for requests behind a proxy.

    Args:
        request: FastAPI Request object

    Returns:
        Client IP address string
    """
    # Check for forwarded header (behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs; first is the client
        return forwarded.split(",")[0].strip()

    # Direct connection
    if request.client:
        return request.client.host

    return "unknown"


async def get_request_context(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> dict:
    """
    Get context information about the current request.

    Useful for logging and analytics.

    Args:
        request: FastAPI Request object
        current_user: Current user (may be None)

    Returns:
        Dict with user_id, ip, user_agent, and path
    """
    return {
        "user_id": current_user.id if current_user else None,
        "ip": get_client_ip(request),
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "path": request.url.path
    }
