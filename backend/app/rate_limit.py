"""
AegisAI — Shared Rate Limiter
Single slowapi Limiter instance shared across routers (avoids circular
imports between app.main and app.routers.*).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Higher budget for authenticated browsing; strict per-endpoint limits
# (see routers/auth.py) protect credential endpoints from brute force.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
)
