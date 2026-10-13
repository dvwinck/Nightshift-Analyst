"""User model.

fastapi-users ships a SQLAlchemy 2.0 declarative table (``Mapped[...]`` columns) which
cannot be mixed into a ``SQLModel`` table class. ``User`` is therefore a plain
declarative model that shares ``SQLModel.metadata``, so the other (SQLModel) tables can
still reference ``users.id`` in their foreign keys and ``create_all`` sees every table.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi_users import schemas
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from pydantic import Field
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlmodel import SQLModel

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50


class Base(DeclarativeBase):
    """Declarative base sharing SQLModel's metadata."""

    metadata = SQLModel.metadata


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User database model."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(USERNAME_MAX_LENGTH), unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserRead(schemas.BaseUser[UUID]):
    """User read schema."""

    username: str
    created_at: datetime
    updated_at: datetime


class UserCreate(schemas.BaseUserCreate):
    """User creation schema."""

    username: str = Field(min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH)


class UserUpdate(schemas.BaseUserUpdate):
    """User update schema."""

    username: Optional[str] = Field(
        default=None, min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
