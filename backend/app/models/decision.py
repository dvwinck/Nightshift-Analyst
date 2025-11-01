"""Decision model."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Relationship


class DecisionType(str, Enum):
    """Decision type enum."""

    INTERROGATE = "interrogate"
    SEARCH = "search"
    ARREST = "arrest"
    RELEASE = "release"
    ANALYZE_EVIDENCE = "analyze_evidence"
    CONSULT = "consult"


class DecisionOutcome(str, Enum):
    """Decision outcome enum."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    NEUTRAL = "neutral"


class DecisionBase(SQLModel):
    """Base decision model."""

    decision_type: DecisionType
    description: str
    outcome: Optional[DecisionOutcome] = None
    stress_impact: int = 0
    reputation_impact: int = 0
    time_taken_minutes: int = 5


class Decision(DecisionBase, table=True):
    """Decision database model."""

    __tablename__ = "decisions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    case_id: UUID = Field(foreign_key="cases.id")
    character_id: Optional[UUID] = Field(default=None, foreign_key="characters.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Decision details
    input_data: Optional[str] = None  # JSON string
    result_data: Optional[str] = None  # JSON string
    clue_discovered: bool = False
    evidence_obtained: bool = False

    # Relationships
    case: Optional["Case"] = Relationship(back_populates="decisions")


class DecisionCreate(DecisionBase):
    """Decision creation schema."""

    case_id: UUID
    character_id: Optional[UUID] = None
    input_data: Optional[str] = None


class DecisionRead(DecisionBase):
    """Decision read schema."""

    id: UUID
    case_id: UUID
    character_id: Optional[UUID]
    created_at: datetime
    input_data: Optional[str]
    result_data: Optional[str]
    clue_discovered: bool
    evidence_obtained: bool


class DecisionUpdate(SQLModel):
    """Decision update schema."""

    outcome: Optional[DecisionOutcome] = None
    stress_impact: Optional[int] = None
    reputation_impact: Optional[int] = None
    result_data: Optional[str] = None
    clue_discovered: Optional[bool] = None
    evidence_obtained: Optional[bool] = None
