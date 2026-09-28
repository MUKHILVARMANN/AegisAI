"""AegisAI — Authentication & Authorization package."""
from app.auth.password import hash_password, verify_password
from app.auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.auth.dependencies import get_current_user, require_role

__all__ = [
    "hash_password", "verify_password",
    "create_access_token", "create_refresh_token", "decode_token",
    "get_current_user", "require_role",
]
