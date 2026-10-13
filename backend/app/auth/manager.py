"""User manager for authentication."""

from typing import Optional, Union
from uuid import UUID

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions, schemas
from loguru import logger
from sqlalchemy import func, select

from app.config import settings
from app.models.user import User
from app.auth.database import get_user_db


MIN_PASSWORD_LENGTH = 8


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """User manager class."""

    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def validate_password(self, password: str, user: Union[schemas.UC, User]) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise exceptions.InvalidPasswordException(
                reason="Password must be at least %d characters." % MIN_PASSWORD_LENGTH
            )

    async def _ensure_username_is_free(
        self, username: Optional[str], owner_id: Optional[UUID] = None
    ) -> None:
        """Raise ``UserAlreadyExists`` (-> HTTP 400) instead of a raw DB IntegrityError."""
        if username is None:
            return
        result = await self.user_db.session.execute(
            select(User.id).where(func.lower(User.username) == username.lower())
        )
        existing_ids = result.scalars().all()
        if any(existing_id != owner_id for existing_id in existing_ids):
            raise exceptions.UserAlreadyExists()

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> User:
        await self._ensure_username_is_free(getattr(user_create, "username", None))
        return await super().create(user_create, safe=safe, request=request)

    async def update(
        self,
        user_update: schemas.UU,
        user: User,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> User:
        await self._ensure_username_is_free(
            getattr(user_update, "username", None), owner_id=user.id
        )
        return await super().update(user_update, user, safe=safe, request=request)

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after user registration."""
        logger.info("User {} registered", user.id)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after forgot password request."""
        logger.info("Password reset requested for user {}", user.id)
        if settings.DEBUG:
            logger.debug("Password reset token for user {}: {}", user.id, token)

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after verification request."""
        logger.info("Verification requested for user {}", user.id)
        if settings.DEBUG:
            logger.debug("Verification token for user {}: {}", user.id, token)


async def get_user_manager(user_db=Depends(get_user_db)):
    """Get user manager instance."""
    yield UserManager(user_db)
