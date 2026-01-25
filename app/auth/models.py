"""
JobKit - Authentication Models

SQLAlchemy models for users and OAuth accounts.

# =============================================================================
# TODO: Multi-User Authentication (Feature 2) - Implement these models
# =============================================================================
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class User(Base):
    """
    User model for authentication.

    TODO: Implement this model:

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # Null for OAuth-only users
    name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    companies = relationship("Company", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("MessageHistory", back_populates="user", cascade="all, delete-orphan")
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # TODO: Add relationships when user_id is added to other models
    # oauth_accounts = relationship("OAuthAccount", back_populates="user")
    # profile = relationship("UserProfile", back_populates="user", uselist=False)


class OAuthAccount(Base):
    """
    OAuth account linked to a user.

    Allows users to login via multiple OAuth providers (Google, GitHub, etc.)

    TODO: Implement this model:

    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)  # "google", "github"
    provider_user_id = Column(String, nullable=False)  # ID from the OAuth provider
    access_token = Column(String)  # Encrypted OAuth access token
    refresh_token = Column(String)  # Encrypted OAuth refresh token (if provided)
    expires_at = Column(DateTime)  # Token expiration
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")

    # Unique constraint: one account per provider per user
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uix_provider_user"),
    )
    """
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String, nullable=False)
    provider_user_id = Column(String, nullable=False)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # TODO: Add relationship when implementing
    # user = relationship("User", back_populates="oauth_accounts")


class RefreshToken(Base):
    """
    Refresh token for JWT token rotation.

    TODO: Implement this model:

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
