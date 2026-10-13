"""Shift routes: start a shift, send commands, replay the log.

The client sends *intent* (a command string). All outcomes are computed by the engine on the
server; the response carries only player-visible text and a sanitized view of the state.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.database import get_session
from app.engine.models import Event
from app.engine.view import ShiftView, build_view
from app.models.shift import Shift
from app.models.user import User
from app.services import shifts as service

router = APIRouter()


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=200)


class ShiftResponse(BaseModel):
    id: str
    started_at: datetime
    view: ShiftView


class CommandResponse(BaseModel):
    accepted: bool
    events: List[Event]
    shift: ShiftResponse


class LogEntry(BaseModel):
    seq: int
    command: str
    accepted: bool
    events: List[Event]
    created_at: datetime


def _shift_response(shift: Shift) -> ShiftResponse:
    view = build_view(service.state_of(shift), service.content_for(shift))
    return ShiftResponse(id=str(shift.id), started_at=shift.started_at, view=view)


async def _current_or_404(session: AsyncSession, user: User) -> Shift:
    try:
        return await service.get_current_shift(session, user)
    except service.NoShift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No shift yet. Start one first.")


@router.post("/", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def start_shift(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Start a new shift. 409 while a previous one is still in progress."""
    try:
        shift = await service.start_shift(session, user)
    except service.ShiftAlreadyActive:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A shift is already in progress.")
    return _shift_response(shift)


@router.get("/current", response_model=ShiftResponse)
async def get_current_shift(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """The latest shift (in progress or finished)."""
    return _shift_response(await _current_or_404(session, user))


@router.post("/current/commands", response_model=CommandResponse)
async def send_command(
    body: CommandRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Run one command. A rejected command still answers 200 with ``accepted=false``."""
    shift = await _current_or_404(session, user)
    try:
        shift, events, accepted = await service.run_command(session, shift, body.command)
    except service.StaleShift:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Shift changed; retry the command.")
    return CommandResponse(accepted=accepted, events=events, shift=_shift_response(shift))


@router.get("/current/log", response_model=List[LogEntry])
async def get_log(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Replay of the most recent commands, oldest first, so the terminal can restore itself."""
    shift = await _current_or_404(session, user)
    entries = await service.recent_log(session, shift, limit)
    return [
        LogEntry(
            seq=e.seq,
            command=e.command,
            accepted=e.accepted,
            events=[Event.model_validate(x) for x in e.events],
            created_at=e.created_at,
        )
        for e in entries
    ]
