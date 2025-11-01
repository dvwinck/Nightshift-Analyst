"""Character model."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class CharacterRole(str, Enum):
    """Character role enum."""

    SUSPECT = "suspect"
    WITNESS = "witness"
    VICTIM = "victim"
    INFORMANT = "informant"


class CharacterBase(SQLModel):
    """Base character model."""

    name: str
    role: CharacterRole
    description: str
    personality_traits: str  # JSON string
    suspicion_level: int = 0  # 0-100
    trust_level: int = 50  # 0-100
    is_guilty: bool = False


class Character(CharacterBase, table=True):
    """Character database model."""

    __tablename__ = "characters"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    case_id: UUID = Field(foreign_key="cases.id")
    dialogue_history: Optional[str] = None  # JSON string
    testimony: Optional[str] = None
    alibi: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CharacterCreate(CharacterBase):
    """Character creation schema."""

    case_id: UUID


class CharacterRead(CharacterBase):
    """Character read schema."""

    id: UUID
    case_id: UUID
    dialogue_history: Optional[str]
    testimony: Optional[str]
    alibi: Optional[str]
    created_at: datetime
    updated_at: datetime


class CharacterUpdate(SQLModel):
    """Character update schema."""

    suspicion_level: Optional[int] = None
    trust_level: Optional[int] = None
    dialogue_history: Optional[str] = None
    testimony: Optional[str] = None
    alibi: Optional[str] = None
