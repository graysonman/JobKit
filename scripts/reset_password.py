#!/usr/bin/env python3
"""
JobKit - Password Reset CLI

Reset a user's password from the command line.
Useful when there's no email service configured.

Usage:
    python scripts/reset_password.py user@email.com newpassword123
"""
import sys
import os

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.auth.models import User, RefreshToken
from app.auth.service import auth_service


def reset_password(email: str, new_password: str):
    init_db()
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: No user found with email '{email}'")
            sys.exit(1)

        # Validate password strength
        try:
            auth_service._validate_password_strength(new_password)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        # Hash and set new password
        user.hashed_password = auth_service.hash_password(new_password)

        # Revoke all refresh tokens (force re-login everywhere)
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False
        ).update({"revoked": True})

        db.commit()
        print(f"Password reset successfully for {email}")
        print("All active sessions have been revoked. The user must log in again.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/reset_password.py <email> <new_password>")
        print("Example: python scripts/reset_password.py user@example.com MyNewPass123")
        sys.exit(1)

    reset_password(sys.argv[1], sys.argv[2])
