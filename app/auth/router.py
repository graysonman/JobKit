"""
JobKit - Authentication Router

API endpoints for user authentication.

Endpoints:
    POST /auth/register           - Email/password registration
    POST /auth/login              - Email/password login -> JWT tokens
    POST /auth/refresh            - Refresh access token
    POST /auth/logout             - Revoke refresh token
    GET  /auth/me                 - Get current user
    PATCH /auth/me                - Update current user
    POST /auth/change-password    - Change password
    POST /auth/set-password       - Set password for OAuth-only users
    POST /auth/send-verification  - Resend verification email
    GET  /auth/verify-email       - Verify email from link
    POST /auth/forgot-password    - Request password reset email
    POST /auth/reset-password     - Reset password with token
    GET  /auth/status             - Check auth system status
    DELETE /auth/account          - Delete user account
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging

from ..database import get_db
from ..config import settings
from ..rate_limit import limiter, RATE_LIMIT_AUTH
from .models import User
from .schemas import (
    UserCreate, UserResponse, UserUpdate,
    Token, TokenRefresh, PasswordChange,
    RegisterResponse, LoginResponse, OAuthAccountResponse,
    PasswordReset, PasswordResetConfirm, DeleteAccountRequest
)
from .service import auth_service, AuthServiceError
from .dependencies import (
    get_current_user,
    get_current_active_user,
    require_auth_available,
    is_single_user_mode
)
from .tokens import (
    generate_verification_token, verify_verification_token,
    generate_reset_token, verify_reset_token,
)
from ..services.email_service import email_service

logger = logging.getLogger("jobkit.auth")
router = APIRouter()


# -----------------------------------------------------------------------------
# Auth Status & Info
# -----------------------------------------------------------------------------

@router.get("/status")
async def get_auth_status():
    """
    Get authentication system status.

    Returns information about:
    - Whether auth is available (dependencies installed)
    - Whether single-user mode is enabled
    - Token expiration settings
    """
    # Include configured OAuth providers so the login page can show/hide buttons
    oauth_providers = []
    if settings.auth.google_client_id and settings.auth.google_client_secret:
        oauth_providers.append("google")
    if settings.auth.github_client_id and settings.auth.github_client_secret:
        oauth_providers.append("github")

    return {
        "available": auth_service.is_available(),
        "single_user_mode": is_single_user_mode(),
        "oauth_providers": oauth_providers,
        "dependencies_installed": {
            "jwt": auth_service.is_available(),
            "password_hashing": auth_service.is_available()
        },
        "settings": {
            "access_token_expire_minutes": settings.auth.access_token_expire_minutes,
            "refresh_token_expire_days": settings.auth.refresh_token_expire_days
        }
    }


# -----------------------------------------------------------------------------
# Registration & Login
# -----------------------------------------------------------------------------

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_AUTH)
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_available)
):
    """
    Register a new user with email and password.

    Requires:
    - Valid email address
    - Password with at least 8 characters, including uppercase, lowercase, and number

    Returns the created user and a success message.
    """
    # Check if single-user mode
    if is_single_user_mode():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration disabled in single-user mode"
        )

    try:
        user = auth_service.create_user(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            db=db
        )

        # Send verification email (fire-and-forget — don't block registration)
        if email_service.is_configured():
            try:
                token = generate_verification_token(user.id, user.email)
                await email_service.send_verification_email(
                    to_email=user.email,
                    token=token,
                    user_name=user.name or "",
                )
            except Exception as e:
                logger.warning("Failed to send verification email: %s", e)

        return RegisterResponse(
            user=_user_to_response(user),
            message="Registration successful. Please check your email to verify your account."
        )

    except AuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(RATE_LIMIT_AUTH)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_available)
):
    """
    Login with email and password to get JWT tokens.

    Uses OAuth2 password flow for compatibility with OpenAPI/Swagger UI.
    The 'username' field should contain the email address.

    Returns:
    - User info
    - Access token (short-lived, for API requests)
    - Refresh token (long-lived, for getting new access tokens)
    """
    # Check if single-user mode
    if is_single_user_mode():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login not required in single-user mode"
        )

    # Authenticate user
    user = auth_service.authenticate_user(
        email=form_data.username,  # OAuth2 form uses 'username' field
        password=form_data.password,
        db=db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Create tokens
    access_token, _ = auth_service.create_access_token(user)
    refresh_token, _ = auth_service.create_refresh_token(user, db)

    return LoginResponse(
        user=_user_to_response(user),
        token=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.auth.access_token_expire_minutes * 60
        )
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_available)
):
    """
    Refresh the access token using a valid refresh token.

    Implements token rotation: the old refresh token is revoked
    and a new one is issued for security.
    """
    # Verify refresh token
    user = auth_service.verify_refresh_token(token_data.refresh_token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Revoke old refresh token (token rotation)
    auth_service.revoke_refresh_token(token_data.refresh_token, db)

    # Create new tokens
    access_token, _ = auth_service.create_access_token(user)
    new_refresh_token, _ = auth_service.create_refresh_token(user, db)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.auth.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Logout by revoking the refresh token.

    The access token will remain valid until it expires,
    but the refresh token cannot be used to get new access tokens.
    """
    revoked = auth_service.revoke_refresh_token(token_data.refresh_token, db)

    if not revoked:
        # Token not found, but still return success (idempotent)
        pass

    return {"message": "Successfully logged out"}


@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout from all devices by revoking all refresh tokens.

    This will force re-authentication on all devices.
    """
    count = auth_service.revoke_all_user_tokens(current_user.id, db)

    return {
        "message": f"Logged out from all devices",
        "tokens_revoked": count
    }


# -----------------------------------------------------------------------------
# Current User
# -----------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current authenticated user's profile.
    """
    return _user_to_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile.

    Only provided fields are updated.
    """
    update_data = user_data.model_dump(exclude_unset=True)

    # Check email uniqueness if changing email
    if "email" in update_data and update_data["email"] != current_user.email:
        existing = db.query(User).filter(User.email == update_data["email"]).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        # Reset verification status when email changes
        current_user.is_verified = False

    # Update fields
    for key, value in update_data.items():
        setattr(current_user, key, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    return _user_to_response(current_user)


# -----------------------------------------------------------------------------
# Password Management
# -----------------------------------------------------------------------------

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_available)
):
    """
    Change the current user's password.

    Requires the current password for verification.
    All refresh tokens are revoked after password change.
    """
    # Check if user has a password
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses OAuth login. Use 'set-password' to add a password."
        )

    # Verify current password
    if not auth_service.verify_password(
        password_data.current_password,
        current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    try:
        auth_service.update_password(current_user, password_data.new_password, db)
    except AuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {"message": "Password changed successfully. Please log in again."}


@router.post("/set-password")
async def set_password(
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_available)
):
    """
    Set a password for an OAuth-only account.

    This allows users who signed up via OAuth to also login with password.
    """
    if current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already has a password. Use 'change-password' instead."
        )

    try:
        auth_service.update_password(current_user, new_password, db)
    except AuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return {"message": "Password set successfully. You can now login with email and password."}


@router.post("/check-password-strength")
async def check_password_strength(password: str):
    """
    Check password strength without creating an account.

    Useful for real-time password validation in the UI.
    """
    result = auth_service.check_password_strength(password)
    return result


# -----------------------------------------------------------------------------
# Email Verification
# -----------------------------------------------------------------------------

@router.post("/send-verification")
@limiter.limit(RATE_LIMIT_AUTH)
async def send_verification(
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """
    Resend the verification email for the current user.

    Rate limited to prevent abuse.
    """
    if current_user.is_verified:
        return {"message": "Email already verified."}

    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service not configured. Contact the administrator.",
        )

    token = generate_verification_token(current_user.id, current_user.email)
    sent = await email_service.send_verification_email(
        to_email=current_user.email,
        token=token,
        user_name=current_user.name or "",
    )

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later.",
        )

    return {"message": "Verification email sent. Check your inbox."}


@router.get("/verify-email")
async def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Verify a user's email from the link in the verification email.

    Returns an HTML page that redirects to login on success.
    """
    data = verify_verification_token(token)
    if not data:
        return HTMLResponse(
            content="""<!DOCTYPE html>
<html><head><title>Verification Failed</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 60px;">
<h2 style="color: #dc2626;">Invalid or Expired Link</h2>
<p>This verification link is invalid or has expired.</p>
<p><a href="/login" style="color: #2563eb;">Go to login</a> and request a new one from your account settings.</p>
</body></html>""",
            status_code=400,
        )

    user = db.query(User).filter(User.id == data["uid"]).first()
    if not user:
        return HTMLResponse(
            content="<html><body><p>User not found.</p></body></html>",
            status_code=404,
        )

    if not user.is_verified:
        user.is_verified = True
        user.updated_at = datetime.utcnow()
        db.commit()

    return HTMLResponse(
        content="""<!DOCTYPE html>
<html><head><title>Email Verified</title>
<meta http-equiv="refresh" content="3;url=/login"></head>
<body style="font-family: sans-serif; text-align: center; padding: 60px;">
<h2 style="color: #16a34a;">Email Verified!</h2>
<p>Your email has been verified successfully. Redirecting to login...</p>
<p><a href="/login" style="color: #2563eb;">Click here if not redirected</a></p>
</body></html>"""
    )


# -----------------------------------------------------------------------------
# Password Reset
# -----------------------------------------------------------------------------

@router.post("/forgot-password")
@limiter.limit(RATE_LIMIT_AUTH)
async def forgot_password(
    request: Request,
    data: PasswordReset,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email.

    Always returns success to prevent email enumeration — an attacker
    cannot determine which emails have accounts.
    """
    user = auth_service.get_user_by_email(data.email, db)

    if user and user.hashed_password and email_service.is_configured():
        token = generate_reset_token(user.id, user.email)
        try:
            await email_service.send_password_reset_email(
                to_email=user.email,
                token=token,
                user_name=user.name or "",
            )
        except Exception as e:
            logger.warning("Failed to send password reset email: %s", e)

    # Always return success to prevent email enumeration
    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit(RATE_LIMIT_AUTH)
async def reset_password(
    request: Request,
    data: PasswordResetConfirm,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_available),
):
    """
    Reset password using a token from the reset email.

    The token is valid for 1 hour. After reset, all refresh tokens
    are revoked to force re-login on all devices.
    """
    token_data = verify_reset_token(data.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link. Please request a new one.",
        )

    user = db.query(User).filter(User.id == token_data["uid"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    try:
        auth_service.update_password(user, data.new_password, db)
    except AuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {"message": "Password reset successfully. You can now log in with your new password."}


# -----------------------------------------------------------------------------
# Account Management
# -----------------------------------------------------------------------------

@router.delete("/account")
async def delete_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete the current user's account.

    This is irreversible and will delete all associated data.
    Password is required if the account has one set.
    """
    # In single-user mode, don't allow deleting the local user
    if is_single_user_mode() and current_user.email == "local@jobkit.local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the local user in single-user mode"
        )

    # Require password verification for accounts that have a password
    if current_user.hashed_password:
        if not payload.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required to delete your account"
            )
        if not auth_service.verify_password(payload.password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password"
            )

    # Revoke all tokens first
    auth_service.revoke_all_user_tokens(current_user.id, db)

    # Delete user (cascade should handle related records)
    db.delete(current_user)
    db.commit()

    return {"message": "Account deleted successfully"}


@router.get("/oauth-accounts", response_model=list[OAuthAccountResponse])
async def list_oauth_accounts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List OAuth accounts linked to the current user.
    """
    accounts = auth_service.get_user_oauth_accounts(current_user.id, db)
    return [
        OAuthAccountResponse(
            id=acc.id,
            provider=acc.provider,
            created_at=acc.created_at
        )
        for acc in accounts
    ]


@router.delete("/oauth-accounts/{provider}")
async def unlink_oauth_account(
    provider: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Unlink an OAuth account from the current user.

    Cannot unlink the last OAuth account if user has no password.
    """
    try:
        success = auth_service.unlink_oauth_account(current_user.id, provider, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {provider} account linked"
            )
        return {"message": f"{provider.title()} account unlinked"}
    except AuthServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# -----------------------------------------------------------------------------
# OAuth2 (requires authlib)
# -----------------------------------------------------------------------------

@router.get("/oauth/{provider}")
async def oauth_login(provider: str, request: Request):
    """
    Redirect to OAuth provider for authentication.

    Supported providers: google, github (when configured)
    """
    from .oauth import is_oauth_configured, get_oauth_client

    if not is_oauth_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' is not configured. "
                   f"Set JOBKIT_{provider.upper()}_CLIENT_ID and "
                   f"JOBKIT_{provider.upper()}_CLIENT_SECRET environment variables."
        )

    client = get_oauth_client(provider)
    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await client.authorize_redirect(request, str(redirect_uri))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from provider.

    Exchanges the authorization code for tokens and creates/updates the user.
    """
    from .oauth import (
        is_oauth_configured, get_oauth_client,
        extract_google_user_info, extract_github_user_info
    )
    import httpx

    if not is_oauth_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' is not configured"
        )

    client = get_oauth_client(provider)

    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )

    # Extract user info based on provider
    if provider == "google":
        user_info = token.get("userinfo")
        if not user_info:
            user_info = await client.userinfo()
        info = extract_google_user_info(dict(user_info))
    elif provider == "github":
        access_token = token.get("access_token")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as http:
            resp = await http.get("https://api.github.com/user", headers=headers)
            user_data = resp.json()
            # GitHub requires separate call for emails
            emails_resp = await http.get("https://api.github.com/user/emails", headers=headers)
            emails_data = emails_resp.json()
        info = extract_github_user_info(user_data, emails_data)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )

    if not info.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not retrieve email from OAuth provider"
        )

    # Get or create user
    user = auth_service.get_or_create_oauth_user(
        email=info["email"],
        name=info.get("name"),
        provider=provider,
        provider_user_id=info["provider_user_id"],
        access_token=token.get("access_token"),
        db=db
    )

    # Create JWT tokens
    access_token, _ = auth_service.create_access_token(user)
    refresh_token, _ = auth_service.create_refresh_token(user, db)

    # Return an HTML page that stores tokens in localStorage then redirects.
    # This is necessary because OAuth callbacks happen via browser redirect,
    # so we can't return JSON — we need to store tokens client-side.
    expires_in = settings.auth.access_token_expire_minutes * 60
    import json as _json
    nonce = getattr(request.state, "nonce", "")
    html_content = f"""<!DOCTYPE html>
<html><head><title>Signing in...</title></head>
<body>
<p>Signing in, please wait...</p>
<script nonce="{nonce}">
localStorage.setItem('jobkit_access_token', {_json.dumps(access_token)});
localStorage.setItem('jobkit_refresh_token', {_json.dumps(refresh_token)});
localStorage.setItem('jobkit_token_expires', String(Date.now() + {expires_in} * 1000));
localStorage.setItem('jobkit_user_name', {_json.dumps(user.name or "")});
localStorage.setItem('jobkit_user_email', {_json.dumps(user.email or "")});
localStorage.setItem('jobkit_is_admin', '{"true" if user.is_admin else "false"}');
window.location.href = '/';
</script>
</body></html>"""
    return HTMLResponse(content=html_content)


@router.get("/oauth/providers")
async def list_oauth_providers():
    """
    List configured OAuth providers.
    """
    from .oauth import list_configured_providers

    providers = list_configured_providers()

    return {
        "configured": providers,
        "available": ["google", "github"],
        "setup_instructions": {
            "google": "Set JOBKIT_GOOGLE_CLIENT_ID and JOBKIT_GOOGLE_CLIENT_SECRET",
            "github": "Set JOBKIT_GITHUB_CLIENT_ID and JOBKIT_GITHUB_CLIENT_SECRET"
        }
    }


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _user_to_response(user: User) -> UserResponse:
    """Convert User model to UserResponse schema."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_admin=user.is_admin,
        created_at=user.created_at,
        has_password=user.hashed_password is not None
    )
