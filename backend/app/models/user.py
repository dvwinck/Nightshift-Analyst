"""User model."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    """Base user model."""

    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False


class User(UserBase, SQLAlchemyBaseUserTableUUID, table=True):
    """User database model."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(SQLModel):
    """User creation schema."""

    email: str
    username: str
    password: str


class UserRead(UserBase):
    """User read schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    """User update schema."""

    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
