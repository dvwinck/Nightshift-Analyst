import pytest

from app.engine.models import Condition, Effects, Response
from app.engine.rules import apply_command, format_clock, holds, new_shift
from tests.engine.helpers import tiny_content


def _start():
    content = tiny_content()
    state, events = new_shift(content)
    return content, state, events


def _read_then(content, state, command):
    state, _, ok = apply_command(state, "read alert-1", content)
    assert ok
    return apply_command(state, command, content)


def test_new_shift_starts_at_content_metrics_and_announces_minute_zero_mail():
    content, state, events = _start()

    assert (state.technical, state.ethical, state.political, state.fatigue) == (50, 50, 50, 0)
    assert state.announced == ["alert-1"]
    assert [e.kind for e in events] == ["info", "message"]


def test_free_commands_cost_no_time_and_change_nothing():
    content, state, _ = _start()

    for command in ("help", "status", "inbox"):
        new, events, ok = apply_command(state, command, content)
        assert ok and new == state and events


def test_read_costs_two_minutes_marks_read_and_shows_body():
    content, state, _ = _start()

    new, events, ok = apply_command(state, "read alert-1", content)

    assert ok and new.clock == 2 and new.read == ["alert-1"]
    assert "Disk at 95%." in events[0].text and "execute (Clean it)" in events[0].text


def test_acting_requires_reading_first():
    content, state, _ = _start()

    new, events, ok = apply_command(state, "execute alert-1", content)

    assert not ok and new == state and "Read alert-1" in events[0].text


def test_execute_applies_effects_shows_deltas_and_costs_verb_minutes():
    content, state, _ = _start()

    new, events, ok = _read_then(content, state, "execute alert-1")

    assert ok
    assert (new.technical, new.ethical) == (55, 47)
    assert new.clock == 2 + 5
    assert new.flags == ["cleaned"] and new.resolved == {"alert-1": "execute"}
    assert "Technical +5 | Ethical -3" in events[0].text


def test_metrics_are_clamped_to_0_100():
    content = tiny_content()
    state, _ = new_shift(content)
    state.technical = 98
    state.ethical = 1

    new, _, _ = _read_then(content, state, "execute alert-1")

    assert new.technical == 100 and new.ethical == 0


def test_delay_once_keeps_the_message_open_and_a_second_delay_is_rejected():
    content, state, _ = _start()
    delayed, _, ok = _read_then(content, state, "delay alert-1")
    assert ok and "alert-1" not in delayed.resolved and delayed.tried == ["delay:alert-1"]

    again, events, ok = apply_command(delayed, "delay alert-1", content)

    assert not ok and again == delayed and "already used delay" in events[0].text
    done, _, ok = apply_command(delayed, "deny alert-1", content)
    assert ok and done.resolved["alert-1"] == "deny"


def test_investigate_gathers_information_but_leaves_the_message_open_for_a_decision():
    content = tiny_content()
    content.messages[0].responses["investigate"] = Response(
        label="Dig", text="You dig.", effects=Effects(set_flags=["dug"], minutes=3)
    )
    state, _ = new_shift(content)
    state, _, _ = apply_command(state, "read alert-1", content)

    dug, events, ok = apply_command(state, "investigate alert-1", content)

    assert ok and "dug" in dug.flags and "alert-1" not in dug.resolved
    assert dug.clock == state.clock + 10 + 3  # verb cost + effect minutes
    again, events, ok = apply_command(dug, "investigate alert-1", content)
    assert not ok and again == dug and "already used investigate" in events[0].text
    decided, _, ok = apply_command(dug, "execute alert-1", content)
    assert ok and decided.resolved["alert-1"] == "execute"


def test_resolved_messages_cannot_be_acted_on_again():
    content, state, _ = _start()
    done, _, _ = _read_then(content, state, "deny alert-1")

    new, events, ok = apply_command(done, "execute alert-1", content)

    assert not ok and new == done and "already resolved" in events[0].text


def test_overdue_message_times_out_once_with_its_penalty():
    content = tiny_content()
    state, _ = new_shift(content)
    state.read.append("alert-1")
    state.clock = 59

    new, events, ok = apply_command(state, "read alert-1", content)  # +2 min -> clock 61 > 60

    assert ok and new.resolved == {"alert-1": "timeout"} and new.technical == 42
    assert [e.kind for e in events if e.kind == "timeout"] == ["timeout"]
    assert "technical -8" in events[-1].text.lower() or "Technical -8" in events[-1].text


def test_arrival_is_gated_by_flags_and_time():
    content, state, _ = _start()
    acted, _, _ = _read_then(content, state, "execute alert-1")  # clock 7, flag set, too early
    assert "order-2" not in acted.announced

    later, events, ok = apply_command(acted, "read alert-1", content)  # alert-1 resolved -> rejected
    assert not ok
    advanced = acted.model_copy(deep=True)
    advanced.clock = 29
    delivered_state, _, _ = apply_command(advanced, "clockout", content)  # ends shift, no arrival needed
    assert delivered_state.ending == "good"

    blocked = tiny_content()
    s2, _ = new_shift(blocked)
    s2.clock = 100  # time is right but the flag was never set
    s2, _, _ = apply_command(s2, "status", blocked)
    from app.engine.rules import _settle  # the delivery step on its own

    _settle(s2, blocked, [])
    assert "order-2" not in s2.announced
    s2.flags.append("cleaned")
    _settle(s2, blocked, [])
    assert "order-2" in s2.announced


def test_a_late_arriving_message_is_not_expired_in_the_same_breath():
    """It must be visible and answerable first: no penalty for a message the player never saw."""
    content = tiny_content()
    for message in content.messages:
        if message.id == "order-2":
            message.expires_at = 40  # authored deadline already passed when the flag unlocks it
    state, _ = new_shift(content)
    state.flags.append("cleaned")

    new, events, ok = apply_command(state, "wait 50", content)

    assert ok and "order-2" in new.announced and "order-2" not in new.resolved
    assert not any(e.kind == "timeout" for e in events)
    assert new.announced_at["order-2"] == 50
    later, events, ok = apply_command(new, "wait 30", content)  # delivered at 50 + 30 min grace
    assert later.resolved["order-2"] == "timeout"


def test_messages_expire_exactly_at_their_deadline_not_a_minute_before():
    content = tiny_content()
    state, _ = new_shift(content)

    before, _, _ = apply_command(state, "wait 59", content)  # alert-1 expires at 60
    at, events, _ = apply_command(before, "wait 1", content)

    assert "alert-1" not in before.resolved
    assert at.resolved["alert-1"] == "timeout" and at.technical == 42
    assert any(e.kind == "timeout" for e in events)


def test_the_shift_ends_exactly_at_the_shift_length():
    content = tiny_content()  # 120 minutes
    state, _ = new_shift(content)

    almost, _, _ = apply_command(state, "wait 60", content)
    almost, _, _ = apply_command(almost, "wait 59", content)
    over, _, _ = apply_command(almost, "wait 1", content)

    assert almost.clock == 119 and almost.ending is None
    assert over.clock == 120 and over.ending is not None


@pytest.mark.parametrize(
    "command",
    ["wait ²", "wait ①", "wait ¹", "wait ٣", "wait ３", "wait " + "9" * 5000, "wait 1e1", "wait +5", "wait 5.5"],
)
def test_wait_never_raises_on_exotic_digits(command):
    content, state, _ = _start()

    new, events, ok = apply_command(state, command, content)

    assert not ok and new == state and events[0].kind == "error"


@pytest.mark.parametrize("command", ["clockout now please", "status foo", "inbox x", "help me", "wait 5 5"])
def test_commands_that_take_no_argument_reject_extra_words(command):
    content, state, _ = _start()

    new, events, ok = apply_command(state, command, content)

    assert not ok and new == state and events[0].kind == "error"


def test_read_and_actions_take_exactly_one_argument():
    content, state, _ = _start()

    for command in ("read alert-1 alert-1", "execute", "deny alert-1 x"):
        new, events, ok = apply_command(state, command, content)
        assert not ok and "Usage" in events[0].text, command


def test_clockout_is_refused_before_the_earliest_allowed_minute():
    content = tiny_content(earliest_clockout_minutes=60)
    state, _ = new_shift(content)

    early, events, ok = apply_command(state, "clockout", content)
    assert not ok and early == state and "cannot clock out before 23:00" in events[0].text

    state, _, _ = apply_command(state, "wait 60", content)
    out, _, ok = apply_command(state, "clockout", content)
    assert ok and out.ending is not None


def test_deny_costs_three_minutes_and_delay_one():
    content, state, _ = _start()
    read, _, _ = apply_command(state, "read alert-1", content)  # clock 2

    delayed, _, _ = apply_command(read, "delay alert-1", content)
    denied, _, _ = apply_command(read, "deny alert-1", content)

    assert delayed.clock == 2 + 1
    assert denied.clock == 2 + 3


def test_fatigue_is_clamped_at_100():
    content, state, _ = _start()
    state.fatigue = 98
    state.clock = 58

    new, _, _ = apply_command(state, "read alert-1", content)  # crosses an hour: +5

    assert new.fatigue == 100


def test_a_new_shift_starts_from_the_content_metrics():
    content = tiny_content(start={"technical": 10, "ethical": 20, "political": 30})

    state, _ = new_shift(content)

    assert (state.technical, state.ethical, state.political) == (10, 20, 30)


def test_inbox_lists_messages_in_arrival_order_marks_unread_and_shows_deadlines():
    content = tiny_content()
    state, _ = new_shift(content)
    state.flags.append("cleaned")
    state, _, _ = apply_command(state, "wait 30", content)  # order-2 arrives
    state, _, _ = apply_command(state, "read alert-1", content)

    _, events, ok = apply_command(state, "inbox", content)

    lines = events[0].text.split("\n")
    assert ok and len(lines) == 2
    assert lines[0].startswith("  alert-1") and "(due 23:00)" in lines[0]  # read -> no star
    assert lines[1].startswith("* order-2") and "due" not in lines[1]  # unread -> star, never expires


def test_status_reports_all_four_values():
    content, state, _ = _start()
    state.fatigue = 7

    _, events, _ = apply_command(state, "status", content)

    assert events[0].text == "22:00 | Technical 50 | Ethical 50 | Political 50 | Fatigue 7"


def test_the_same_flag_set_twice_is_stored_once():
    content = tiny_content()
    content.messages[1].responses["execute"].effects.set_flags.append("cleaned")
    state, _ = new_shift(content)
    state.flags.append("cleaned")
    state.clock = 30
    state, _, _ = apply_command(state, "wait 1", content)  # delivers order-2
    state, _, _ = apply_command(state, "read order-2", content)

    state, _, _ = apply_command(state, "execute order-2", content)

    assert state.flags.count("cleaned") == 1


def test_content_that_loses_a_message_does_not_crash_a_running_shift():
    content, state, _ = _start()
    state.announced.append("ghost-9")  # a shift that was started before this id was removed

    _, events, ok = apply_command(state, "inbox", content)
    _, errors, rejected = apply_command(state, "read ghost-9", content)

    assert ok and "alert-1" in events[0].text and "ghost-9" not in events[0].text
    assert not rejected and errors[0].kind == "error"


@pytest.mark.parametrize(
    "condition,state_values,expected",
    [
        ({}, {}, True),
        ({"min": {"political": 60}}, {"political": 60}, True),  # inclusive lower bound
        ({"min": {"political": 60}}, {"political": 59}, False),
        ({"max": {"ethical": 40}}, {"ethical": 40}, True),  # inclusive upper bound
        ({"max": {"ethical": 40}}, {"ethical": 41}, False),
        ({"min": {"fatigue": 50}}, {"fatigue": 49}, False),
        ({"flags_all": ["a", "b"]}, {"flags": ["a", "b"]}, True),
        ({"flags_all": ["a", "b"]}, {"flags": ["a"]}, False),
        ({"flags_none": ["a"]}, {"flags": []}, True),
        ({"flags_none": ["a"]}, {"flags": ["a"]}, False),
        ({"min": {"technical": 55}, "flags_none": ["x"]}, {"technical": 55, "flags": ["x"]}, False),
    ],
)
def test_holds_truth_table(condition, state_values, expected):
    state, _ = new_shift(tiny_content())
    for key, value in state_values.items():
        setattr(state, key, value)

    assert holds(Condition.model_validate(condition), state) is expected
def test_fatigue_accrues_five_per_hour_crossed():
    content, state, _ = _start()
    state.clock = 58

    new, _, _ = apply_command(state, "read alert-1", content)  # crosses minute 60

    assert new.fatigue == 5


def test_shift_ends_at_the_deadline_with_highest_priority_matching_ending():
    content, state, _ = _start()
    state.flags.append("cleaned")
    state.clock = 119

    new, events, ok = apply_command(state, "read alert-1", content)

    assert ok and new.ending == "good" and events[-1].kind == "ending"


def test_catch_all_ending_when_nothing_else_matches():
    content, state, _ = _start()
    state.clock = 119

    new, _, _ = apply_command(state, "read alert-1", content)

    assert new.ending == "plain"


def test_commands_after_the_end_are_rejected():
    content, state, _ = _start()
    ended, _, _ = apply_command(state, "clockout", content)

    new, events, ok = apply_command(ended, "status", content)

    assert ended.ending is not None and not ok and new == ended and "over" in events[0].text


def test_apply_command_never_mutates_its_input():
    content, state, _ = _start()
    snapshot = state.model_copy(deep=True)

    apply_command(state, "read alert-1", content)
    apply_command(state, "clockout", content)

    assert state == snapshot


def test_bad_input_is_rejected_without_changing_state():
    content, state, _ = _start()
    for raw in ("", "   ", "dance", "read", "read a b", "execute nope-9", "READ alert-99"):
        new, events, ok = apply_command(state, raw, content)
        assert not ok and new == state and events[0].kind == "error", raw


def test_commands_are_case_and_whitespace_insensitive():
    content, state, _ = _start()

    new, _, ok = apply_command(state, "  READ   Alert-1 ", content)

    assert ok and new.read == ["alert-1"]


def test_clock_label_wraps_past_midnight():
    content = tiny_content()

    assert format_clock(content, 0) == "22:00"
    assert format_clock(content, 150) == "00:30"


def test_wait_passes_time_so_late_mail_can_arrive():
    content = tiny_content()
    state, _ = new_shift(content)
    state.flags.append("cleaned")

    new, events, ok = apply_command(state, "wait 30", content)

    assert ok and new.clock == 30 and "order-2" in new.announced
    assert any("NEW order-2" in e.text for e in events)


def test_wait_defaults_to_fifteen_minutes_and_validates_its_argument():
    content, state, _ = _start()

    new, _, ok = apply_command(state, "wait", content)
    assert ok and new.clock == 15

    for raw in ("wait 0", "wait 61", "wait -5", "wait abc", "wait 5 5"):
        rejected, events, ok = apply_command(state, raw, content)
        assert not ok and rejected == state and events[0].kind == "error", raw
