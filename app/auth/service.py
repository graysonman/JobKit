"""
JobKit - Authentication Service

Core authentication logic including password hashing, JWT handling, and user management.

Setup:
    pip install python-jose[cryptography] passlib[bcrypt]

Features:
- Bcrypt password hashing
- JWT access token creation/validation
- Refresh token management with rotation
- User creation and authentication
- OAuth user linking
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import secrets
import logging

# Check for optional dependencies
try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    JWTError = Exception  # Placeholder

try:
    from passlib.context import CryptContext
    PASSLIB_AVAILABLE = True
except ImportError:
    PASSLIB_AVAILABLE = False

from sqlalchemy.orm import Session

from ..config import settings
from .models import User, RefreshToken, OAuthAccount
from .schemas import TokenData

logger = logging.getLogger("jobkit.auth")


class AuthServiceError(Exception):
    """Custom exception for authentication errors."""
    pass


class AuthService:
    """
    Authentication service for user management and JWT handling.

    Provides:
    - Password hashing with bcrypt
    - JWT access/refresh token management
    - User creation and authentication
    - OAuth account linking
    """

    def __init__(self):
        """Initialize auth service with password context."""
        self._pwd_context = None
        if PASSLIB_AVAILABLE:
            self._pwd_context = CryptContext(
                schemes=["bcrypt"],
                deprecated="auto",
                bcrypt__rounds=12  # Good balance of security and speed
            )

    def _check_dependencies(self) -> None:
        """Check if required dependencies are installed."""
        missing = []
        if not JWT_AVAILABLE:
            missing.append("python-jose[cryptography]")
        if not PASSLIB_AVAILABLE:
            missing.append("passlib[bcrypt]")

        if missing:
            raise AuthServiceError(
                f"Auth dependencies not installed. Run: pip install {' '.join(missing)}"
            )

    def is_available(self) -> bool:
        """Check if auth service has all required dependencies."""
        return JWT_AVAILABLE and PASSLIB_AVAILABLE

    # -------------------------------------------------------------------------
    # Password Hashing
    # -------------------------------------------------------------------------

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string

        Raises:
            AuthServiceError: If passlib is not installed
        """
        if not PASSLIB_AVAILABLE or not self._pwd_context:
            raise AuthServiceError(
                "passlib not installed. Run: pip install passlib[bcrypt]"
            )
        return self._pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Previously hashed password

        Returns:
            True if password matches, False otherwise
        """
        if not PASSLIB_AVAILABLE or not self._pwd_context:
            logger.error("passlib not installed - cannot verify password")
            return False

        try:
            return self._pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Check password strength and return feedback.

        Args:
            password: Password to check

        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []

        if len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if len(password) > 128:
            errors.append("Password must be less than 128 characters")
        if not any(c.isupper() for c in password):
            errors.append("Password should contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            errors.append("Password should contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            errors.append("Password should contain at least one number")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": "strong" if len(errors) == 0 else "weak"
        }

    # -------------------------------------------------------------------------
    # JWT Token Management
    # -------------------------------------------------------------------------

    def create_access_token(
        self,
        user: User,
        expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, datetime]:
        """
        Create a JWT access token.

        Args:
            user: User to create token for
            expires_delta: Optional custom expiration time

        Returns:
            Tuple of (token_string, expiration_datetime)

        Raises:
            AuthServiceError: If python-jose is not installed
        """
        if not JWT_AVAILABLE:
            raise AuthServiceError(
                "python-jose not installed. Run: pip install python-jose[cryptography]"
            )

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.auth.access_token_expire_minutes
            )

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        token = jwt.encode(
            payload,
            settings.auth.secret_key,
            algorithm=settings.auth.algorithm
        )

        logger.debug(f"Created access token for user {user.id}")
        return token, expire

    def create_refresh_token(self, user: User, db: Session) -> Tuple[str, datetime]:
        """
        Create a refresh token and store it in the database.

        Uses secure random token generation (not JWT) for refresh tokens.

        Args:
            user: User to create token for
            db: Database session

        Returns:
            Tuple of (token_string, expiration_datetime)
        """
        expire = datetime.utcnow() + timedelta(
            days=settings.auth.refresh_token_expire_days
        )

        # Generate secure random token
        token = secrets.token_urlsafe(32)

        # Store in database
        db_token = RefreshToken(
            user_id=user.id,
            token=token,
            expires_at=expire
        )
        db.add(db_token)
        db.commit()

        logger.debug(f"Created refresh token for user {user.id}")
        return token, expire

    def verify_access_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode an access token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None if invalid/expired
        """
        if not JWT_AVAILABLE:
            logger.error("python-jose not installed - cannot verify token")
            return None

        try:
            payload = jwt.decode(
                token,
                settings.auth.secret_key,
                algorithms=[settings.auth.algorithm]
            )

            # Verify token type
            if payload.get("type") != "access":
                logger.warning("Token is not an access token")
                return None

            # Extract user info
            user_id = payload.get("sub")
            email = payload.get("email")

            if not user_id or not email:
                logger.warning("Token missing required claims")
                return None

            return TokenData(
                user_id=int(user_id),
                email=email,
                exp=datetime.fromtimestamp(payload["exp"])
            )

        except JWTError as e:
            logger.debug(f"Token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None

    def verify_refresh_token(self, token: str, db: Session) -> Optional[User]:
        """
        Verify a refresh token and return the associated user.

        Args:
            token: Refresh token string
            db: Database session

        Returns:
            User if valid, None if invalid/expired/revoked
        """
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()

        if not db_token:
            logger.debug("Refresh token not found or expired")
            return None

        user = db.query(User).filter(User.id == db_token.user_id).first()

        if not user:
            logger.warning(f"User {db_token.user_id} not found for refresh token")
            return None

        if not user.is_active:
            logger.warning(f"User {user.id} is inactive")
            return None

        return user

    def revoke_refresh_token(self, token: str, db: Session) -> bool:
        """
        Revoke a refresh token (logout).

        Args:
            token: Refresh token to revoke
            db: Database session

        Returns:
            True if token was revoked, False if not found
        """
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == token
        ).first()

        if db_token:
            db_token.revoked = True
            db.commit()
            logger.debug(f"Revoked refresh token for user {db_token.user_id}")
            return True

        return False

    def revoke_all_user_tokens(self, user_id: int, db: Session) -> int:
        """
        Revoke all refresh tokens for a user (logout from all devices).

        Args:
            user_id: User ID to revoke tokens for
            db: Database session

        Returns:
            Number of tokens revoked
        """
        count = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False
        ).update({"revoked": True})

        db.commit()
        logger.info(f"Revoked {count} refresh tokens for user {user_id}")
        return count

    def cleanup_expired_tokens(self, db: Session) -> int:
        """
        Delete expired refresh tokens from database.

        Should be run periodically (e.g., daily) to clean up old tokens.

        Args:
            db: Database session

        Returns:
            Number of tokens deleted
        """
        count = db.query(RefreshToken).filter(
            RefreshToken.expires_at < datetime.utcnow()
        ).delete()

        db.commit()
        logger.info(f"Cleaned up {count} expired refresh tokens")
        return count

    # -------------------------------------------------------------------------
    # User Management
    # -------------------------------------------------------------------------

    def create_user(
        self,
        email: str,
        password: str,
        name: Optional[str],
        db: Session
    ) -> User:
        """
        Create a new user with email/password.

        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            name: Optional display name
            db: Database session

        Returns:
            Created User instance

        Raises:
            AuthServiceError: If user already exists or password invalid
        """
        self._check_dependencies()

        # Check if user already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise AuthServiceError("User with this email already exists")

        # Validate password
        strength = self.check_password_strength(password)
        if not strength["valid"]:
            raise AuthServiceError(f"Weak password: {strength['errors'][0]}")

        # Create user
        hashed = self.hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed,
            name=name,
            is_active=True,
            is_verified=False  # Email verification required
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Created new user: {user.id} ({email})")
        return user

    def authenticate_user(
        self,
        email: str,
        password: str,
        db: Session
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User if credentials valid, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.debug(f"User not found: {email}")
            return None

        if not user.hashed_password:
            logger.debug(f"User {email} is OAuth-only (no password)")
            return None

        if not self.verify_password(password, user.hashed_password):
            logger.debug(f"Invalid password for user: {email}")
            return None

        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {email}")
            return None

        logger.info(f"User authenticated: {user.id} ({email})")
        return user

    def get_user_by_id(self, user_id: int, db: Session) -> Optional[User]:
        """
        Get a user by their ID.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            User if found, None otherwise
        """
        return db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str, db: Session) -> Optional[User]:
        """
        Get a user by their email.

        Args:
            email: User's email address
            db: Database session

        Returns:
            User if found, None otherwise
        """
        return db.query(User).filter(User.email == email).first()

    def update_password(
        self,
        user: User,
        new_password: str,
        db: Session
    ) -> bool:
        """
        Update a user's password.

        Args:
            user: User to update
            new_password: New plain text password
            db: Database session

        Returns:
            True if successful
        """
        self._check_dependencies()

        # Validate new password
        strength = self.check_password_strength(new_password)
        if not strength["valid"]:
            raise AuthServiceError(f"Weak password: {strength['errors'][0]}")

        user.hashed_password = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()

        # Revoke all existing refresh tokens (security measure)
        self.revoke_all_user_tokens(user.id, db)

        logger.info(f"Password updated for user {user.id}")
        return True

    # -------------------------------------------------------------------------
    # OAuth Support
    # -------------------------------------------------------------------------

    def get_or_create_oauth_user(
        self,
        email: str,
        name: Optional[str],
        provider: str,
        provider_user_id: str,
        access_token: Optional[str],
        db: Session
    ) -> User:
        """
        Get or create a user from OAuth login.

        If user exists with this email, links the OAuth account.
        If user doesn't exist, creates a new user.

        Args:
            email: User's email from OAuth provider
            name: User's name from OAuth provider
            provider: OAuth provider name (e.g., "google", "github")
            provider_user_id: User's ID from the OAuth provider
            access_token: OAuth access token (optional, for API calls)
            db: Database session

        Returns:
            User instance (existing or newly created)
        """
        # Check if OAuth account already exists
        existing_oauth = db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        ).first()

        if existing_oauth:
            # Return existing user
            user = db.query(User).filter(User.id == existing_oauth.user_id).first()
            if user:
                # Update access token if provided
                if access_token:
                    existing_oauth.access_token = access_token
                    db.commit()
                logger.debug(f"OAuth login for existing user {user.id}")
                return user

        # Check if user exists with this email
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Create new user
            user = User(
                email=email,
                name=name,
                is_active=True,
                is_verified=True  # OAuth users are auto-verified
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new OAuth user: {user.id} ({email})")

        # Link OAuth account
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token
        )
        db.add(oauth_account)
        db.commit()

        logger.info(f"Linked {provider} OAuth account to user {user.id}")
        return user

    def get_user_oauth_accounts(self, user_id: int, db: Session) -> list:
        """
        Get all OAuth accounts linked to a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            List of OAuthAccount instances
        """
        return db.query(OAuthAccount).filter(
            OAuthAccount.user_id == user_id
        ).all()

    def unlink_oauth_account(
        self,
        user_id: int,
        provider: str,
        db: Session
    ) -> bool:
        """
        Unlink an OAuth account from a user.

        Args:
            user_id: User ID
            provider: OAuth provider to unlink
            db: Database session

        Returns:
            True if unlinked, False if not found
        """
        # Check user has a password or another OAuth account
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        oauth_accounts = self.get_user_oauth_accounts(user_id, db)

        if not user.hashed_password and len(oauth_accounts) <= 1:
            raise AuthServiceError(
                "Cannot unlink last OAuth account without setting a password"
            )

        # Delete the OAuth account
        deleted = db.query(OAuthAccount).filter(
            OAuthAccount.user_id == user_id,
            OAuthAccount.provider == provider
        ).delete()

        db.commit()
        return deleted > 0


# Global service instance
auth_service = AuthService()


# Convenience functions
def hash_password(password: str) -> str:
    """Hash a password using the global auth service."""
    return auth_service.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password using the global auth service."""
    return auth_service.verify_password(plain_password, hashed_password)


def create_access_token(user: User) -> Tuple[str, datetime]:
    """Create an access token using the global auth service."""
    return auth_service.create_access_token(user)
