"""Game state model."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class GameStateBase(SQLModel):
    """Base game state model."""

    current_day: int = 1
    stress_level: int = 0  # 0-100
    reputation: int = 50  # 0-100
    cases_solved: int = 0
    cases_failed: int = 0
    total_playtime_minutes: int = 0
    current_case_id: Optional[UUID] = None


class GameState(GameStateBase, table=True):
    """Game state database model."""

    __tablename__ = "game_states"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True)
    last_played: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Game progression
    unlocked_features: str = "[]"  # JSON array of unlocked features
    achievements: str = "[]"  # JSON array of achievements


class GameStateCreate(GameStateBase):
    """Game state creation schema."""

    user_id: UUID


class GameStateRead(GameStateBase):
    """Game state read schema."""

    id: UUID
    user_id: UUID
    last_played: datetime
    created_at: datetime
    updated_at: datetime
    unlocked_features: str
    achievements: str


class GameStateUpdate(SQLModel):
    """Game state update schema."""

    current_day: Optional[int] = None
    stress_level: Optional[int] = None
    reputation: Optional[int] = None
    cases_solved: Optional[int] = None
    cases_failed: Optional[int] = None
    total_playtime_minutes: Optional[int] = None
    current_case_id: Optional[UUID] = None
    last_played: Optional[datetime] = None
    unlocked_features: Optional[str] = None
    achievements: Optional[str] = None
