from app.engine.rules import apply_command, format_clock, new_shift
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
    assert ok and "alert-1" not in delayed.resolved and delayed.delayed == ["alert-1"]

    again, events, ok = apply_command(delayed, "delay alert-1", content)

    assert not ok and again == delayed and "already delayed" in events[0].text
    done, _, ok = apply_command(delayed, "deny alert-1", content)
    assert ok and done.resolved["alert-1"] == "deny"


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


def test_message_arriving_after_its_expiry_expires_immediately():
    content = tiny_content()
    for message in content.messages:
        if message.id == "order-2":
            message.expires_at = 40
    state, _ = new_shift(content)
    state.flags.append("cleaned")
    state.clock = 50

    from app.engine.rules import _settle

    events = []
    _settle(state, content, events)

    assert state.resolved.get("order-2") == "timeout"
    assert [e.kind for e in events].count("timeout") >= 1


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
