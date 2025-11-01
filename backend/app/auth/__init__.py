"""Authentication module."""

from app.auth.manager import get_user_manager
from app.auth.backend import auth_backend
from app.auth.users import fastapi_users, current_active_user

__all__ = [
    "get_user_manager",
    "auth_backend",
    "fastapi_users",
    "current_active_user",
]
