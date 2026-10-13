"""Use-cases around a shift: load/save state, call the engine, write the log.

Routes stay thin and the engine stays pure; everything that touches the database for a
shift lives here.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.content import DEFAULT_SHIFT, get_shift_content
from app.engine.models import Event, ShiftContent, ShiftState
from app.engine.rules import apply_command, new_shift
from app.models.shift import ActionLog, Shift
from app.models.user import User


class ShiftAlreadyActive(Exception):
    """The user already has an unfinished shift."""


class NoShift(Exception):
    """The user has never started a shift."""


class StaleShift(Exception):
    """Another request changed the shift while this command was being processed."""


def _events_json(events: List[Event]) -> List[dict]:
    return [e.model_dump() for e in events]


def content_for(shift: Shift) -> ShiftContent:
    return get_shift_content(shift.content_name)


def state_of(shift: Shift) -> ShiftState:
    return ShiftState.model_validate(shift.state)


async def get_current_shift(session: AsyncSession, user: User) -> Shift:
    """The user's most recent shift (active or finished)."""
    result = await session.execute(
        select(Shift).where(Shift.user_id == user.id).order_by(Shift.started_at.desc()).limit(1)
    )
    shift = result.scalar_one_or_none()
    if shift is None:
        raise NoShift()
    return shift


async def start_shift(session: AsyncSession, user: User) -> Shift:
    """Begin a new shift, refusing if one is still in progress."""
    try:
        current = await get_current_shift(session, user)
    except NoShift:
        current = None
    if current is not None and current.ended_at is None:
        raise ShiftAlreadyActive()

    content = get_shift_content(DEFAULT_SHIFT)
    state, events = new_shift(content)
    shift = Shift(user_id=user.id, content_name=DEFAULT_SHIFT, state=state.model_dump())
    session.add(shift)
    try:
        await session.flush()  # surfaces the one-active-shift index violation here
    except IntegrityError:
        await session.rollback()
        raise ShiftAlreadyActive()
    session.add(
        ActionLog(shift_id=shift.id, seq=0, command="start", accepted=True, events=_events_json(events))
    )
    await session.commit()
    await session.refresh(shift)
    return shift


async def run_command(
    session: AsyncSession, shift: Shift, raw: str
) -> Tuple[Shift, List[Event], bool]:
    """Apply a command to the shift, persist the new state and log the attempt.

    The state write is a compare-and-set on ``version``: if a concurrent request won, this one
    raises ``StaleShift`` (HTTP 409) rather than silently overwriting it.
    """
    content = content_for(shift)
    new_state, events, accepted = apply_command(state_of(shift), raw, content)
    next_version = shift.version + 1
    ended_at = datetime.utcnow() if new_state.ending is not None else None

    result = await session.execute(
        update(Shift)
        .where(Shift.id == shift.id, Shift.version == shift.version)
        .values(state=new_state.model_dump(), version=next_version, ended_at=ended_at)
    )
    if result.rowcount != 1:
        await session.rollback()
        raise StaleShift()
    session.add(
        ActionLog(
            shift_id=shift.id,
            seq=next_version,
            command=raw,
            accepted=accepted,
            events=_events_json(events),
        )
    )
    await session.commit()
    await session.refresh(shift)
    return shift, events, accepted


async def recent_log(session: AsyncSession, shift: Shift, limit: int) -> List[ActionLog]:
    """The last ``limit`` log entries, oldest first (what the terminal replays on reload)."""
    result = await session.execute(
        select(ActionLog).where(ActionLog.shift_id == shift.id).order_by(ActionLog.seq.desc()).limit(limit)
    )
    return list(reversed(result.scalars().all()))
