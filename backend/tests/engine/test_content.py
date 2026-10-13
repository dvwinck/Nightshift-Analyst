import copy
import json
import random

import pytest
from pydantic import ValidationError

from app.engine.content import CONTENT_DIR, get_shift_content, load_content, validate_content
from app.engine.models import NON_RESOLVING, QUALITIES, ShiftContent
from app.engine.rules import apply_command, new_shift
from app.engine.view import build_view
from tests.engine.helpers import tiny_content


def _raw():
    return json.loads((CONTENT_DIR / "night_one.json").read_text(encoding="utf-8"))


def test_night_one_loads_and_has_no_validation_problems():
    content = get_shift_content("night_one")

    assert validate_content(content) == []
    assert len(content.messages) >= 10 and len(content.endings) >= 5


def test_unknown_keys_are_rejected_so_typos_fail_loudly():
    raw = _raw()
    raw["messages"][0]["responses"]["execute"]["efects"] = {"technical": 1}

    with pytest.raises(ValidationError):
        ShiftContent.model_validate(raw)


def test_validator_reports_duplicates_missing_catch_all_orphan_flags_and_late_arrivals():
    content = tiny_content()
    content.messages.append(copy.deepcopy(content.messages[0]))  # duplicate id
    content.endings = [e for e in content.endings if e.id != "plain"]  # no catch-all
    content.messages[1].requires.flags_all.append("never-set")  # orphan flag
    content.messages[1].arrives_at = 500  # after the 120-minute shift

    errors = "\n".join(validate_content(content))

    assert "duplicate message id: alert-1" in errors
    assert "no catch-all ending" in errors
    assert "flag 'never-set' is required but no outcome ever sets it" in errors
    assert "order-2 arrives after the shift ends" in errors


def test_load_content_lists_every_problem(tmp_path):
    raw = _raw()
    raw["endings"] = [e for e in raw["endings"] if "requires" in e]  # drop the catch-all
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(raw))

    with pytest.raises(ValueError, match="no catch-all ending"):
        load_content(path)


def _random_playthrough(content, rng, max_steps=400):
    state, _ = new_shift(content)
    seen_clock = state.clock
    for _ in range(max_steps):
        if state.ending is not None:
            return state
        options = []
        for message_id in state.announced:
            if message_id in state.resolved:
                continue
            message = content.message(message_id)
            if message_id not in state.read:
                options.append("read " + message_id)
                continue
            for verb in message.responses:
                if verb in NON_RESOLVING and "%s:%s" % (verb, message_id) in state.tried:
                    continue
                options.append("%s %s" % (verb, message_id))
        options.append("wait")  # time must be able to pass even with nothing to do
        if rng.random() < 0.02:
            options.append("clockout")
        if rng.random() < 0.05:
            options.append(rng.choice(["dance", "read", "execute zzz-1", ""]))  # garbage must be harmless
        state, _, _ = apply_command(state, rng.choice(options), content)
        # invariants that must hold after *every* command
        assert state.clock >= seen_clock
        seen_clock = state.clock
        for quality in QUALITIES:
            assert 0 <= getattr(state, quality) <= 100
        assert set(state.resolved) <= set(state.announced)
    raise AssertionError("playthrough did not finish within %d steps" % max_steps)


def test_random_playthroughs_always_finish_and_reach_every_ending():
    content = get_shift_content("night_one")
    rng = random.Random(773)
    reached = set()

    for _ in range(4000):
        reached.add(_random_playthrough(content, rng).ending)

    assert reached == {e.id for e in content.endings}


def test_public_view_never_leaks_unread_bodies_effects_or_requirements():
    content = get_shift_content("night_one")
    state, _ = new_shift(content)

    view = build_view(state, content)
    dumped = view.model_dump_json()

    assert view.inbox and all(m.body is None and m.verbs == [] for m in view.inbox)
    for secret in ('"effects"', '"requires"', "set_flags", "on_timeout", "purged_77b"):
        assert secret not in dumped

    state, _, _ = apply_command(state, "read order-773", content)
    opened = next(m for m in build_view(state, content).inbox if m.id == "order-773")
    assert opened.body and [v.verb for v in opened.verbs] == ["execute", "deny", "delay", "investigate"]


def test_used_non_resolving_verbs_disappear_from_the_public_view():
    content = get_shift_content("night_one")
    state, _ = new_shift(content)
    state, _, _ = apply_command(state, "read order-773", content)
    state, _, _ = apply_command(state, "investigate order-773", content)

    opened = next(m for m in build_view(state, content).inbox if m.id == "order-773")

    assert [v.verb for v in opened.verbs] == ["execute", "deny", "delay"]
