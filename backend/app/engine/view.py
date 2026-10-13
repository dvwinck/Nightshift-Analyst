"""What the client may see. Effects, requirements and unread message bodies never leave the server."""

from typing import List, Optional

from pydantic import BaseModel

from app.engine.models import NON_RESOLVING, ShiftContent, ShiftState
from app.engine.rules import deadline, format_clock, open_messages


class VerbView(BaseModel):
    verb: str
    label: str


class MessageView(BaseModel):
    id: str
    category: str
    priority: int
    sender: str
    title: str
    read: bool
    #: Wall-clock label (e.g. "00:30") after which the message expires, if it ever does.
    due: Optional[str] = None
    body: Optional[str] = None
    verbs: List[VerbView] = []


class MetricsView(BaseModel):
    technical: int
    ethical: int
    political: int
    fatigue: int


class EndingView(BaseModel):
    id: str
    title: str
    text: str


class ShiftView(BaseModel):
    clock: int
    clock_label: str
    remaining_minutes: int
    metrics: MetricsView
    inbox: List[MessageView]
    ending: Optional[EndingView] = None


def build_view(state: ShiftState, content: ShiftContent) -> ShiftView:
    inbox: List[MessageView] = []
    for message_id in open_messages(state):
        message = content.message(message_id)
        if message is None:  # content changed under a running shift; never crash the view
            continue
        is_read = message_id in state.read
        due = deadline(state, message)
        inbox.append(
            MessageView(
                id=message.id,
                category=message.category,
                priority=message.priority,
                sender=message.sender,
                title=message.title,
                read=is_read,
                due=None if due is None else format_clock(content, due),
                body=message.body if is_read else None,
                verbs=[
                    VerbView(verb=v, label=r.label)
                    for v, r in message.responses.items()
                    if is_read and not (v in NON_RESOLVING and "%s:%s" % (v, message_id) in state.tried)
                ],
            )
        )
    ending = None
    if state.ending is not None:
        chosen = next((e for e in content.endings if e.id == state.ending), None)
        if chosen is not None:
            ending = EndingView(id=chosen.id, title=chosen.title, text=chosen.text)
    return ShiftView(
        clock=state.clock,
        clock_label=format_clock(content, state.clock),
        remaining_minutes=max(0, content.shift_length_minutes - state.clock),
        metrics=MetricsView(
            technical=state.technical,
            ethical=state.ethical,
            political=state.political,
            fatigue=state.fatigue,
        ),
        inbox=inbox,
        ending=ending,
    )
