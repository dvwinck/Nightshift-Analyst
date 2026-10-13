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
    assert "flag 'never-set' is used in a condition but no outcome ever sets it" in errors
    assert "order-2 can never be delivered" in errors
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


def test_validator_finds_circular_flags_unresolvable_messages_and_shadowed_endings():
    content = tiny_content()
    # order-2 needs 'cleaned' and is now the only thing that could set 'loop'; 'loop' gates itself
    content.messages[1].requires.flags_all = ["loop"]
    content.messages[1].responses["execute"].effects.set_flags = ["loop"]
    content.messages[0].responses = {k: v for k, v in content.messages[0].responses.items() if k == "delay"}
    content.messages[0].expires_at = None
    content.messages[0].on_timeout = None
    content.endings[0].priority = 0  # 'good' is now outranked by the catch-all at priority 0? no: equal
    content.endings[1].priority = 9  # the catch-all outranks 'good'

    errors = "\n".join(validate_content(content))

    assert "order-2 can never be delivered" in errors
    assert "alert-1 can never be resolved" in errors
    assert "ending 'good' can never be chosen: the catch-all with priority 9 outranks it" in errors


def test_validator_rejects_a_clockout_time_after_the_shift_and_starting_metrics_out_of_range():
    content = tiny_content()
    content.earliest_clockout_minutes = 999
    assert "earliest_clockout_minutes is later" in "\n".join(validate_content(content))

    with pytest.raises(ValidationError):
        tiny_content(start={"technical": 500, "ethical": -20, "political": 50})


def test_flags_that_are_only_negated_are_still_checked_for_typos():
    content = tiny_content()
    content.messages[1].requires.flags_none = ["claned"]  # typo: would silently never block

    assert "flag 'claned' is used in a condition" in "\n".join(validate_content(content))


def test_duplicate_keys_in_a_content_file_are_an_error_not_a_silent_overwrite(tmp_path):
    path = tmp_path / "dup.json"
    path.write_text('{"title": "a", "title": "b"}')

    with pytest.raises(ValueError, match="duplicate key"):
        load_content(path)


def _play(script, content=None):
    content = content or get_shift_content("night_one")
    state, _ = new_shift(content)
    for command in script:
        state, events, accepted = apply_command(state, command, content)
        assert accepted, (command, [e.text for e in events])
    while state.ending is None:
        state, _, _ = apply_command(state, "wait 60", content)
    return state


def test_a_principled_path_reaches_daylight():
    state = _play(
        [
            "read order-773", "deny order-773",            # refuse the purge
            "wait 30", "read chat-12", "execute chat-12",   # trust Okafor
            "wait 60", "read chat-13", "execute chat-13",   # take the copy
            "wait 60", "wait 60", "read intel-402", "execute intel-402",  # leak it
        ]
    )

    assert state.ending == "daylight"


def test_a_compliant_competent_path_reaches_company_analyst():
    """Obedience alone is not enough: ignored alerts erode Technical and the Director's offer
    (order-776) must be answered, so the careerist has to actually work the whole night."""
    state = _play(
        [
            "read alert-101", "execute alert-101",           # keep the systems healthy
            "read order-773", "execute order-773",           # purge the archive
            "wait 60", "wait 60", "read order-775", "execute order-775",  # sign the report
            "wait 15", "read alert-103", "execute alert-103",  # backups verified
            "wait 60", "wait 60", "wait 15", "read order-776", "execute order-776",  # take the promotion
        ]
    )

    assert state.ending == "company-analyst"


def test_a_careerist_who_ignores_the_night_does_not_get_the_good_company_ending():
    state = _play(["read order-773", "execute order-773"])  # then nothing but waiting

    assert state.ending == "routine-maintenance"


def test_the_clockout_exploit_is_closed():
    content = get_shift_content("night_one")
    state, _ = new_shift(content)
    state, _, _ = apply_command(state, "read order-773", content)
    state, _, _ = apply_command(state, "execute order-773", content)

    state, events, accepted = apply_command(state, "clockout", content)

    assert not accepted and state.ending is None and "02:00" in events[0].text


def test_no_message_is_penalised_in_the_same_command_that_delivers_it():
    content = get_shift_content("night_one")
    rng = random.Random(1)
    for _ in range(1500):
        state, _ = new_shift(content)
        for _ in range(300):
            if state.ending is not None:
                break
            verb = rng.choice(["wait 60", "wait 15", "status"] + ["read " + m for m in state.announced])
            state, events, _ = apply_command(state, verb, content)
            delivered = {e.data["id"] for e in events if e.kind == "message" and e.data.get("new")}
            expired = {e.data["id"] for e in events if e.kind == "timeout"}
            assert not (delivered & expired), (verb, delivered & expired)


ALPHABET = list("abcdefghijklmnopqrstuvwxyz0123456789-_ \t\n") + ["²", "①", "٣", "３", "é", "ｒ", "\x00", "\u200b"]


def test_random_text_never_crashes_never_corrupts_and_a_finished_shift_stays_frozen():
    content = get_shift_content("night_one")
    rng = random.Random(2024)
    state, _ = new_shift(content)
    for _ in range(6000):
        words = [rng.choice(["read", "execute", "deny", "delay", "investigate", "wait", "clockout", "status", "inbox", "help"])]
        words.append(rng.choice(state.announced + ["order-773", "nope-1", "5", "60", "²", ""]) if rng.random() < 0.7 else "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 12))))
        raw = " ".join(words) if rng.random() < 0.8 else "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 40)))
        before = state.model_copy(deep=True)
        new, events, accepted = apply_command(state, raw, content)

        assert state == before  # input never mutated
        assert events
        if not accepted:
            assert new == before and all(e.kind == "error" for e in events), raw
        if before.ending is not None:
            assert new == before and not accepted
        for quality in QUALITIES:
            assert 0 <= getattr(new, quality) <= 100
        assert new.clock >= before.clock
        state = new
        if state.ending is not None:
            state, _ = new_shift(content)
