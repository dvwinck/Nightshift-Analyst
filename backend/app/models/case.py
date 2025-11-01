"""Case model."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship


class CaseStatus(str, Enum):
    """Case status enum."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class CaseDifficulty(str, Enum):
    """Case difficulty enum."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTREME = "extreme"


class CaseBase(SQLModel):
    """Base case model."""

    title: str
    description: str
    difficulty: CaseDifficulty
    status: CaseStatus = CaseStatus.PENDING
    time_limit_minutes: int = 15
    stress_impact: int = 10
    reputation_reward: int = 20


class Case(CaseBase, table=True):
    """Case database model."""

    __tablename__ = "cases"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Evidence and clues
    evidence_data: Optional[str] = None  # JSON string
    clues_found: int = 0
    total_clues: int = 3

    # Relationships
    decisions: list["Decision"] = Relationship(back_populates="case")


class CaseCreate(CaseBase):
    """Case creation schema."""

    user_id: UUID


class CaseRead(CaseBase):
    """Case read schema."""

    id: UUID
    user_id: UUID
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    evidence_data: Optional[str]
    clues_found: int
    total_clues: int


class CaseUpdate(SQLModel):
    """Case update schema."""

    status: Optional[CaseStatus] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    evidence_data: Optional[str] = None
    clues_found: Optional[int] = None
