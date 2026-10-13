"""Persistence for a player's shift and its command log."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel


class Shift(SQLModel, table=True):
    """One play-through of a shift. ``state`` is a serialized ``ShiftState``."""

    __tablename__ = "shifts"
    __table_args__ = (
        # At most one unfinished shift per user, enforced by the database (not just by a check).
        Index(
            "uq_shifts_one_active_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    content_name: str = "night_one"
    state: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    #: Bumped on every command; the compare-and-set that stops two requests clobbering each other.
    version: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None


class ActionLog(SQLModel, table=True):
    """Every command a player sent (accepted or not) and the events it produced."""

    __tablename__ = "action_logs"
    __table_args__ = (UniqueConstraint("shift_id", "seq", name="uq_action_logs_shift_seq"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    shift_id: UUID = Field(foreign_key="shifts.id", index=True, ondelete="CASCADE")
    seq: int
    command: str
    accepted: bool
    events: List[Dict[str, Any]] = Field(sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
