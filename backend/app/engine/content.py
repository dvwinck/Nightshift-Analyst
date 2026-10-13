"""Loading and validating shift content."""

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Set, Union

from app.engine.models import Condition, Outcome, ShiftContent

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content"
DEFAULT_SHIFT = "night_one"


def _condition_flags(condition: Condition) -> Set[str]:
    return set(condition.flags_all) | set(condition.flags_none)


def validate_content(content: ShiftContent) -> List[str]:
    """Return human-readable problems that schema validation alone cannot catch."""
    errors: List[str] = []

    ids = [m.id for m in content.messages]
    errors += ["duplicate message id: %s" % i for i in sorted({i for i in ids if ids.count(i) > 1})]
    ending_ids = [e.id for e in content.endings]
    errors += ["duplicate ending id: %s" % i for i in sorted({i for i in ending_ids if ending_ids.count(i) > 1})]

    if not any(e.requires == Condition() for e in content.endings):
        errors.append("no catch-all ending (an ending with an empty 'requires')")

    produced: Set[str] = set()
    for message in content.messages:
        outcomes: List[Outcome] = list(message.responses.values())
        if message.on_timeout is not None:
            outcomes.append(message.on_timeout)
        for outcome in outcomes:
            produced |= set(outcome.effects.set_flags)
        if message.arrives_at >= content.shift_length_minutes:
            errors.append("%s arrives after the shift ends" % message.id)

    used: Set[str] = set()
    for message in content.messages:
        used |= _condition_flags(message.requires)
    for ending in content.endings:
        used |= _condition_flags(ending.requires)
    errors += ["flag '%s' is required but no outcome ever sets it" % f for f in sorted(used - produced)]
    return errors


def load_content(path: Union[str, Path]) -> ShiftContent:
    """Parse and validate a content file; raises ``ValueError`` listing every problem."""
    content = ShiftContent.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
    errors = validate_content(content)
    if errors:
        raise ValueError("invalid shift content:\n- " + "\n- ".join(errors))
    return content


@lru_cache(maxsize=None)
def get_shift_content(name: str = DEFAULT_SHIFT) -> ShiftContent:
    """Content is immutable at runtime: load once per process."""
    return load_content(CONTENT_DIR / ("%s.json" % name))
