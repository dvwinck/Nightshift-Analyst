"""The rules of a shift as pure functions.

``apply_command(state, raw, content)`` never mutates its input and never touches I/O, so
every rule is unit-testable without a database. The API layer only loads the state, calls
this function, and stores the result.
"""

from typing import List, Optional, Tuple

from app.engine.models import (
    NON_RESOLVING,
    QUALITIES,
    VERB_MINUTES,
    Condition,
    Effects,
    Event,
    Message,
    Outcome,
    ShiftContent,
    ShiftState,
)

#: Commands that cost no shift time.
FREE_COMMANDS = ("help", "status", "inbox")
#: Verbs a player can use on a message (see ``NON_RESOLVING`` for the ones that keep it open).
RESPONSE_VERBS = ("execute", "deny", "delay", "investigate")
#: ``wait`` passes this long by default, and at most ``MAX_WAIT_MINUTES`` per command.
DEFAULT_WAIT_MINUTES = 15
MAX_WAIT_MINUTES = 60
#: Tiredness accrues with the clock: this much fatigue for every full hour that passes.
FATIGUE_PER_HOUR = 5


def format_clock(content: ShiftContent, minutes: int) -> str:
    total = (content.start_hour * 60 + minutes) % (24 * 60)
    return "%02d:%02d" % (total // 60, total % 60)


def holds(condition: Condition, state: ShiftState) -> bool:
    """Whether ``condition`` is satisfied by ``state``."""
    for quality, bound in condition.min.items():
        if getattr(state, quality) < bound:
            return False
    for quality, bound in condition.max.items():
        if getattr(state, quality) > bound:
            return False
    if any(flag not in state.flags for flag in condition.flags_all):
        return False
    return not any(flag in state.flags for flag in condition.flags_none)


def new_shift(content: ShiftContent) -> Tuple[ShiftState, List[Event]]:
    """Start a shift: initial metrics, then whatever is already waiting at minute 0."""
    state = ShiftState(
        technical=content.start.technical,
        ethical=content.start.ethical,
        political=content.start.political,
    )
    events = [Event(kind="info", text=content.intro)]
    _settle(state, content, events)
    return state, events


def apply_command(
    state: ShiftState, raw: str, content: ShiftContent
) -> Tuple[ShiftState, List[Event], bool]:
    """Apply one player command. Returns ``(new_state, events, accepted)``.

    A rejected command (unknown, illegal, shift over) returns the *same* state, an error
    event and ``accepted=False``: it costs no time and changes nothing.
    """
    new = state.model_copy(deep=True)
    if new.ending is not None:
        return state, [_error("The shift is over.")], False

    words = raw.strip().lower().split()
    if not words:
        return state, [_error("Type a command. Try 'help'.")], False
    verb, args = words[0], words[1:]

    if verb in FREE_COMMANDS:
        return state, _free_command(verb, state, content), True
    if verb == "wait":
        minutes = DEFAULT_WAIT_MINUTES
        if args:
            if len(args) != 1 or not args[0].isdigit():
                return state, [_error("Usage: wait [minutes]")], False
            minutes = int(args[0])
        if not 1 <= minutes <= MAX_WAIT_MINUTES:
            return state, [_error("You can wait 1-%d minutes at a time." % MAX_WAIT_MINUTES)], False
        events = [Event(kind="info", text="You watch the console for %d minutes." % minutes)]
        _advance(new, minutes, content, events)
        return new, events, True
    if verb == "clockout":
        events = [Event(kind="info", text="You clock out early.")]
        _finish(new, content, events)
        return new, events, True
    if verb == "read" or verb in RESPONSE_VERBS:
        if len(args) != 1:
            return state, [_error("Usage: %s <message-id>" % verb)], False
        events: List[Event] = []
        error = _message_command(new, verb, args[0], content, events)
        if error is not None:
            return state, [_error(error)], False
        return new, events, True
    return state, [_error("Unknown command '%s'. Try 'help'." % verb)], False


# --------------------------------------------------------------------------- internals


def _error(text: str) -> Event:
    return Event(kind="error", text=text)


def _free_command(verb: str, state: ShiftState, content: ShiftContent) -> List[Event]:
    if verb == "help":
        lines = [
            "help                 this list",
            "status               clock and metrics",
            "inbox                open messages",
            "read <id>            read a message (2 min)",
            "execute|deny <id>    decide a message you have read",
            "delay|investigate <id>   once per message; keeps it open",
            "wait [minutes]       let time pass (default 15, max 60)",
            "clockout             end the shift now",
        ]
        return [Event(kind="info", text="\n".join(lines))]
    if verb == "status":
        text = "%s | Technical %d | Ethical %d | Political %d | Fatigue %d" % (
            format_clock(content, state.clock),
            state.technical,
            state.ethical,
            state.political,
            state.fatigue,
        )
        return [Event(kind="info", text=text, data={"clock": state.clock})]
    open_ids = open_messages(state)
    if not open_ids:
        return [Event(kind="info", text="Inbox empty.")]
    lines = []
    for message_id in open_ids:
        message = content.message(message_id)
        assert message is not None
        mark = " " if message_id in state.read else "*"
        lines.append("%s %s  P%d  %s: %s" % (mark, message.id, message.priority, message.sender, message.title))
    return [Event(kind="info", text="\n".join(lines))]


def open_messages(state: ShiftState) -> List[str]:
    """Announced messages that are not resolved yet, in arrival order."""
    return [m for m in state.announced if m not in state.resolved]


def _message_command(
    state: ShiftState, verb: str, message_id: str, content: ShiftContent, events: List[Event]
) -> Optional[str]:
    """Mutates ``state``/``events`` for a ``read``/response command, or returns an error text."""
    message = content.message(message_id)
    if message is None or message_id not in state.announced:
        return "No such message: %s" % message_id
    if message_id in state.resolved:
        return "%s is already resolved." % message_id

    if verb == "read":
        if message_id not in state.read:
            state.read.append(message_id)
        verbs = ", ".join(
            "%s (%s)" % (v, r.label) for v, r in message.responses.items()
        )
        events.append(
            Event(
                kind="message",
                text="%s\nFrom: %s | Priority %d\n\n%s\n\nOptions: %s"
                % (message.title, message.sender, message.priority, message.body, verbs),
                data={"id": message.id},
            )
        )
        _advance(state, VERB_MINUTES["read"], content, events)
        return None

    if message_id not in state.read:
        return "Read %s before acting on it." % message_id
    response = message.responses.get(verb)  # type: ignore[call-overload]
    if response is None:
        return "%s cannot be used on %s." % (verb, message_id)
    if verb in NON_RESOLVING:
        attempt = "%s:%s" % (verb, message_id)
        if attempt in state.tried:
            return "You already used %s on %s." % (verb, message_id)
        state.tried.append(attempt)
    else:
        state.resolved[message_id] = verb

    deltas = _apply_effects(state, response.effects)
    events.append(
        Event(
            kind="outcome",
            text="[%s] %s%s" % (message.id, response.text, (" " + deltas) if deltas else ""),
            data={"id": message.id, "verb": verb},
        )
    )
    _advance(state, VERB_MINUTES[verb] + response.effects.minutes, content, events)
    return None


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _apply_effects(state: ShiftState, effects: Effects) -> str:
    """Apply metric/flag effects; return the player-visible delta summary."""
    parts = []
    for quality in QUALITIES:
        delta = getattr(effects, quality)
        if delta:
            setattr(state, quality, _clamp(getattr(state, quality) + delta))
            parts.append("%s %+d" % (quality.capitalize(), delta))
    for flag in effects.set_flags:
        if flag not in state.flags:
            state.flags.append(flag)
    if effects.minutes:
        parts.append("+%d min" % effects.minutes)
    return "(" + " | ".join(parts) + ")" if parts else ""


def _advance(state: ShiftState, minutes: int, content: ShiftContent, events: List[Event]) -> None:
    hours_before = state.clock // 60
    state.clock += minutes
    state.fatigue = _clamp(state.fatigue + FATIGUE_PER_HOUR * (state.clock // 60 - hours_before))
    _settle(state, content, events)
    if state.clock >= content.shift_length_minutes and state.ending is None:
        _finish(state, content, events)


def _settle(state: ShiftState, content: ShiftContent, events: List[Event]) -> None:
    """Expire overdue messages and deliver new ones until nothing changes.

    Expiry can set flags that unlock arrivals, and an arrival whose ``expires_at`` has already
    passed expires immediately, so this runs to a fixpoint (bounded by the message count).
    """
    for _ in range(len(content.messages) + 1):
        changed = False
        for message in content.messages:
            if _expire(state, message, events):
                changed = True
        for message in content.messages:
            if _deliver(state, message, events):
                changed = True
        if not changed:
            return


def _expire(state: ShiftState, message: Message, events: List[Event]) -> bool:
    if (
        message.expires_at is None
        or message.id not in state.announced
        or message.id in state.resolved
        or message.expires_at > state.clock
    ):
        return False
    state.resolved[message.id] = "timeout"
    outcome: Optional[Outcome] = message.on_timeout
    if outcome is None:
        events.append(Event(kind="timeout", text="[%s] expired unanswered." % message.id, data={"id": message.id}))
        return True
    deltas = _apply_effects(state, outcome.effects)
    events.append(
        Event(
            kind="timeout",
            text="[%s] %s%s" % (message.id, outcome.text, (" " + deltas) if deltas else ""),
            data={"id": message.id},
        )
    )
    return True


def _deliver(state: ShiftState, message: Message, events: List[Event]) -> bool:
    if (
        message.id in state.announced
        or message.arrives_at > state.clock
        or not holds(message.requires, state)
    ):
        return False
    state.announced.append(message.id)
    events.append(
        Event(
            kind="message",
            text="NEW %s  P%d  %s: %s" % (message.id, message.priority, message.sender, message.title),
            data={"id": message.id, "new": True},
        )
    )
    return True


def _finish(state: ShiftState, content: ShiftContent, events: List[Event]) -> None:
    ordered = sorted(content.endings, key=lambda e: -e.priority)  # stable: ties keep file order
    chosen = next(e for e in ordered if holds(e.requires, state))
    state.ending = chosen.id
    events.append(
        Event(kind="ending", text="%s\n\n%s" % (chosen.title, chosen.text), data={"id": chosen.id})
    )
