"""
JobKit - Authentication Schemas

Pydantic schemas for auth request/response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# -----------------------------------------------------------------------------
# User Schemas
# -----------------------------------------------------------------------------

class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response (public user data)."""
    id: int
    is_active: bool
    is_verified: bool
    is_admin: bool = False
    created_at: datetime
    has_password: bool  # True if user can login with password (vs OAuth-only)

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None


# -----------------------------------------------------------------------------
# Token Schemas
# -----------------------------------------------------------------------------

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class TokenData(BaseModel):
    """Schema for decoded token data (internal use)."""
    user_id: int
    email: str
    exp: datetime


# -----------------------------------------------------------------------------
# Password Schemas
# -----------------------------------------------------------------------------

class PasswordChange(BaseModel):
    """Schema for password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8)


# -----------------------------------------------------------------------------
# OAuth Schemas
# -----------------------------------------------------------------------------

class OAuthAccountResponse(BaseModel):
    """Schema for OAuth account response."""
    id: int
    provider: str
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthCallback(BaseModel):
    """Schema for OAuth callback data."""
    code: str
    state: Optional[str] = None


# -----------------------------------------------------------------------------
# Registration Response
# -----------------------------------------------------------------------------

class RegisterResponse(BaseModel):
    """Schema for registration response."""
    user: UserResponse
    message: str = "Registration successful. Please verify your email."


class LoginResponse(BaseModel):
    """Schema for login response."""
    user: UserResponse
    token: Token


# -----------------------------------------------------------------------------
# Error Schemas
# -----------------------------------------------------------------------------

class AuthError(BaseModel):
    """Schema for authentication errors."""
    detail: str
    error_code: Optional[str] = None


# Error codes for frontend handling
AUTH_ERROR_CODES = {
    "INVALID_CREDENTIALS": "Email or password is incorrect",
    "USER_NOT_FOUND": "No account found with this email",
    "USER_INACTIVE": "Account is deactivated",
    "EMAIL_NOT_VERIFIED": "Please verify your email before logging in",
    "TOKEN_EXPIRED": "Token has expired",
    "TOKEN_INVALID": "Token is invalid",
    "EMAIL_EXISTS": "An account with this email already exists",
    "OAUTH_ERROR": "OAuth authentication failed",
    "PASSWORD_REQUIRED": "This account requires a password (not OAuth-only)",
}
