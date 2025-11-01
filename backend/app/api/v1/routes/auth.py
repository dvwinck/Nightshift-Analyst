"""Authentication routes."""

from fastapi import APIRouter

from app.auth.users import fastapi_users
from app.auth.backend import auth_backend
from app.models.user import UserRead, UserCreate, UserUpdate

router = APIRouter()

# Register authentication routes
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
)

router.include_router(
    fastapi_users.get_reset_password_router(),
)

router.include_router(
    fastapi_users.get_verify_router(UserRead),
)

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
)
