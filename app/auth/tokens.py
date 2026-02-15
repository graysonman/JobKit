"""
JobKit - Token generation for email verification and password reset.

Uses itsdangerous URLSafeTimedSerializer for signed tokens with built-in
expiration. No database storage needed — the token itself encodes the
data + timestamp, signed with the app's secret key.

Different salt values prevent a verification token from being used
as a reset token (and vice versa).
"""
from typing import Optional

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from ..config import settings

_serializer = URLSafeTimedSerializer(settings.auth.secret_key)

VERIFICATION_SALT = "email-verify"
RESET_SALT = "password-reset"


def generate_verification_token(user_id: int, email: str) -> str:
    """Generate a signed token for email verification. Valid for 24 hours."""
    return _serializer.dumps({"uid": user_id, "email": email}, salt=VERIFICATION_SALT)


def verify_verification_token(token: str, max_age: int = 86400) -> Optional[dict]:
    """
    Verify an email verification token.

    Returns {"uid": int, "email": str} or None if invalid/expired.
    Default max_age: 86400 seconds (24 hours).
    """
    try:
        return _serializer.loads(token, salt=VERIFICATION_SALT, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def generate_reset_token(user_id: int, email: str) -> str:
    """Generate a signed token for password reset. Valid for 1 hour."""
    return _serializer.dumps({"uid": user_id, "email": email}, salt=RESET_SALT)


def verify_reset_token(token: str, max_age: int = 3600) -> Optional[dict]:
    """
    Verify a password reset token.

    Returns {"uid": int, "email": str} or None if invalid/expired.
    Default max_age: 3600 seconds (1 hour).
    """
    try:
        return _serializer.loads(token, salt=RESET_SALT, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
