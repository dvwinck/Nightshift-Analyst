"""Loading and validating shift content."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Union

from app.engine.models import NON_RESOLVING, Condition, Outcome, ShiftContent

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content"
DEFAULT_SHIFT = "night_one"


def _condition_flags(condition: Condition) -> Set[str]:
    return set(condition.flags_all) | set(condition.flags_none)


def _produced_by(message) -> Set[str]:
    outcomes: List[Outcome] = list(message.responses.values())
    if message.on_timeout is not None:
        outcomes.append(message.on_timeout)
    produced: Set[str] = set()
    for outcome in outcomes:
        produced |= set(outcome.effects.set_flags)
    return produced


def _reachable_flags(content: ShiftContent) -> Tuple[Set[str], Set[str]]:
    """Fixpoint: which messages can ever be delivered, and which flags can ever be set.

    A message can be delivered once every flag it needs (``flags_all``) is producible by a message
    that can itself be delivered. Metric gates are ignored (they are assumed satisfiable), so this
    only catches impossible *flag* dependencies such as a flag that only its own gate can set.
    """
    producible: Set[str] = set()
    deliverable: Set[str] = set()
    changed = True
    while changed:
        changed = False
        for message in content.messages:
            if message.id in deliverable or not set(message.requires.flags_all) <= producible:
                continue
            deliverable.add(message.id)
            producible |= _produced_by(message)
            changed = True
    return deliverable, producible


def validate_content(content: ShiftContent) -> List[str]:
    """Return human-readable problems that schema validation alone cannot catch."""
    errors: List[str] = []

    ids = [m.id for m in content.messages]
    errors += ["duplicate message id: %s" % i for i in sorted({i for i in ids if ids.count(i) > 1})]
    ending_ids = [e.id for e in content.endings]
    errors += ["duplicate ending id: %s" % i for i in sorted({i for i in ending_ids if ending_ids.count(i) > 1})]

    catch_alls = [e for e in content.endings if e.requires == Condition()]
    if not catch_alls:
        errors.append("no catch-all ending (an ending with an empty 'requires')")
    else:
        top = max(e.priority for e in catch_alls)
        errors += [
            "ending '%s' can never be chosen: the catch-all with priority %d outranks it" % (e.id, top)
            for e in content.endings
            if e.requires != Condition() and e.priority < top
        ]

    for message in content.messages:
        if message.arrives_at >= content.shift_length_minutes:
            errors.append("%s arrives after the shift ends" % message.id)
        if message.expires_at is None and all(verb in NON_RESOLVING for verb in message.responses):
            errors.append(
                "%s can never be resolved: it only offers delay/investigate and never expires" % message.id
            )

    if content.earliest_clockout_minutes > content.shift_length_minutes:
        errors.append("earliest_clockout_minutes is later than the end of the shift")

    deliverable, producible = _reachable_flags(content)
    errors += [
        "%s can never be delivered: it requires flags that no reachable outcome sets" % m.id
        for m in content.messages
        if m.id not in deliverable
    ]
    used: Set[str] = set()
    for message in content.messages:
        used |= _condition_flags(message.requires)
    for ending in content.endings:
        errors += [
            "ending '%s' can never be chosen: flag '%s' is never set" % (ending.id, flag)
            for flag in sorted(set(ending.requires.flags_all) - producible)
        ]
        used |= _condition_flags(ending.requires)
    # Every flag a condition mentions must exist somewhere; a typo in ``flags_none`` would
    # otherwise disable a gate silently, because it is then always satisfied.
    all_produced: Set[str] = set()
    for message in content.messages:
        all_produced |= _produced_by(message)
    errors += ["flag '%s' is used in a condition but no outcome ever sets it" % f for f in sorted(used - all_produced)]
    return errors


def _reject_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    """``json`` silently keeps the last of two equal keys, which would hide a content mistake."""
    seen: Dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key in content file: %r" % key)
        seen[key] = value
    return seen


def load_content(path: Union[str, Path]) -> ShiftContent:
    """Parse and validate a content file; raises ``ValueError`` listing every problem."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    content = ShiftContent.model_validate(raw)
    errors = validate_content(content)
    if errors:
        raise ValueError("invalid shift content:\n- " + "\n- ".join(errors))
    return content


@lru_cache(maxsize=None)
def get_shift_content(name: str = DEFAULT_SHIFT) -> ShiftContent:
    """Content is immutable at runtime: load once per process."""
    return load_content(CONTENT_DIR / ("%s.json" % name))
