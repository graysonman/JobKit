"""
JobKit - Centralized rate limiting configuration.

All rate limit decorators should import `limiter` from this module.
The limiter keys on client IP address (via X-Forwarded-For when behind a proxy).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# --- Rate limit constants ---

# AI-powered endpoints (cost money per Groq API call) — strictest
RATE_LIMIT_AI = "2/minute"

# Auth endpoints (login, register, password reset) — strict to prevent brute force
RATE_LIMIT_AUTH = "5/minute"

# General API write operations (create, update, delete) — moderate
RATE_LIMIT_GENERAL = "30/minute"

# Read-heavy endpoints (search, list, stats) — generous (1/sec sustained)
RATE_LIMIT_READ = "60/minute"

# Admin panel endpoints — moderate (admin traffic is low volume)
RATE_LIMIT_ADMIN = "30/minute"
