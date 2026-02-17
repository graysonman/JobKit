#!/usr/bin/env python3
"""
JobKit - Admin Promotion CLI

Promote or demote a user to/from admin.

Usage:
    python scripts/promote_admin.py user@email.com          # promote
    python scripts/promote_admin.py user@email.com --demote  # demote
"""
import sys
import os

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.auth.models import User


def promote_admin(email: str, demote: bool = False):
    init_db()
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: No user found with email '{email}'")
            sys.exit(1)

        if demote:
            if not user.is_admin:
                print(f"{email} is already not an admin.")
                return
            user.is_admin = False
            db.commit()
            print(f"Demoted {email} — no longer an admin.")
        else:
            if user.is_admin:
                print(f"{email} is already an admin.")
                return
            user.is_admin = True
            db.commit()
            print(f"Promoted {email} to admin.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python scripts/promote_admin.py <email> [--demote]")
        print("Examples:")
        print("  python scripts/promote_admin.py user@example.com          # promote")
        print("  python scripts/promote_admin.py user@example.com --demote  # demote")
        sys.exit(1)

    demote = "--demote" in sys.argv
    email = sys.argv[1]
    promote_admin(email, demote=demote)
