"""Domain models: static shift content, mutable shift state, and the events a command emits.

Content models forbid unknown keys, so a typo in a content file fails loudly at load time
instead of silently doing nothing during play.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Verb = Literal["execute", "deny", "delay", "investigate"]
Category = Literal["order", "alert", "intel", "chat"]
EventKind = Literal["info", "message", "outcome", "timeout", "error", "ending"]

#: Numeric qualities a condition can test. ``technical``/``ethical``/``political`` are the
#: GDD's three metrics; ``fatigue`` is a fourth, purely numeric pressure value.
QUALITIES = ("technical", "ethical", "political", "fatigue")

#: Minutes of shift time each verb costs before the outcome's own ``minutes`` is added.
VERB_MINUTES = {"read": 2, "execute": 5, "deny": 3, "delay": 1, "investigate": 10}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(_Strict):
    """Every listed requirement must hold. An empty condition always holds."""

    min: Dict[str, int] = Field(default_factory=dict)
    max: Dict[str, int] = Field(default_factory=dict)
    flags_all: List[str] = Field(default_factory=list)
    flags_none: List[str] = Field(default_factory=list)

    @field_validator("min", "max")
    @classmethod
    def _known_qualities(cls, value: Dict[str, int]) -> Dict[str, int]:
        unknown = set(value) - set(QUALITIES)
        if unknown:
            raise ValueError("unknown quality: %s" % ", ".join(sorted(unknown)))
        return value


class Effects(_Strict):
    technical: int = 0
    ethical: int = 0
    political: int = 0
    fatigue: int = 0
    minutes: int = Field(default=0, ge=0)
    set_flags: List[str] = Field(default_factory=list)


class Outcome(_Strict):
    text: str
    effects: Effects = Field(default_factory=Effects)


class Response(Outcome):
    """What a verb does to a message. ``label`` is shown to the player in ``help``/``read``."""

    label: str


class TimeoutOutcome(Outcome):
    """Applied once when a message expires unresolved. It cannot cost time itself."""

    @model_validator(mode="after")
    def _no_minutes(self) -> "TimeoutOutcome":
        if self.effects.minutes:
            raise ValueError("a timeout outcome cannot advance the clock")
        return self


class Message(_Strict):
    id: str = Field(pattern=r"^[a-z]+-\d+$")
    category: Category
    priority: int = Field(ge=1, le=5)
    sender: str
    title: str
    body: str
    arrives_at: int = Field(default=0, ge=0)
    requires: Condition = Field(default_factory=Condition)
    responses: Dict[Verb, Response] = Field(min_length=1)
    expires_at: Optional[int] = None
    on_timeout: Optional[TimeoutOutcome] = None

    @model_validator(mode="after")
    def _expiry_after_arrival(self) -> "Message":
        if self.expires_at is not None and self.expires_at <= self.arrives_at:
            raise ValueError("expires_at must be after arrives_at")
        if self.on_timeout is not None and self.expires_at is None:
            raise ValueError("on_timeout needs expires_at")
        return self


class Ending(_Strict):
    id: str
    title: str
    text: str
    requires: Condition = Field(default_factory=Condition)
    priority: int = 0


class StartingMetrics(_Strict):
    technical: int = 50
    ethical: int = 50
    political: int = 50


class ShiftContent(_Strict):
    title: str
    intro: str
    start_hour: int = Field(default=22, ge=0, le=23)
    shift_length_minutes: int = Field(default=480, gt=0)
    start: StartingMetrics = Field(default_factory=StartingMetrics)
    messages: List[Message]
    endings: List[Ending]

    def message(self, message_id: str) -> Optional[Message]:
        for message in self.messages:
            if message.id == message_id:
                return message
        return None


class ShiftState(BaseModel):
    """Everything that changes during a shift. JSON-serializable; stored as-is by the API."""

    clock: int = 0
    technical: int = 50
    ethical: int = 50
    political: int = 50
    fatigue: int = 0
    announced: List[str] = Field(default_factory=list)
    read: List[str] = Field(default_factory=list)
    delayed: List[str] = Field(default_factory=list)
    resolved: Dict[str, str] = Field(default_factory=dict)
    flags: List[str] = Field(default_factory=list)
    ending: Optional[str] = None


class Event(BaseModel):
    kind: EventKind
    text: str
    data: Dict[str, Any] = Field(default_factory=dict)
