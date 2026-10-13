import pytest
from sqlalchemy import select

from app.models.shift import Shift
from app.models.user import User
from app.services import shifts as service

SHIFTS = "/api/v1/shifts"


async def _start(client, headers):
    response = await client.post(SHIFTS + "/", headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _cmd(client, headers, command):
    response = await client.post(SHIFTS + "/current/commands", json={"command": command}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", SHIFTS + "/"),
        ("get", SHIFTS + "/current"),
        ("post", SHIFTS + "/current/commands"),
        ("get", SHIFTS + "/current/log"),
    ],
)
async def test_every_shift_route_requires_a_token(client, method, path):
    response = await getattr(client, method)(path)

    assert response.status_code == 401


async def test_no_shift_yet_is_a_404(client, make_user):
    alice = await make_user()

    assert (await client.get(SHIFTS + "/current", headers=alice)).status_code == 404
    response = await client.post(SHIFTS + "/current/commands", json={"command": "status"}, headers=alice)
    assert response.status_code == 404
    assert (await client.get(SHIFTS + "/current/log", headers=alice)).status_code == 404


async def test_starting_a_shift_returns_a_sanitized_view_and_the_intro_in_the_log(client, make_user):
    alice = await make_user()

    shift = await _start(client, alice)

    view = shift["view"]
    assert view["clock_label"] == "22:00" and view["ending"] is None
    assert {m["id"] for m in view["inbox"]} == {"alert-101", "order-773"}
    assert all(m["read"] is False and m["body"] is None and m["verbs"] == [] for m in view["inbox"])
    for secret in ("effects", "requires", "set_flags", "on_timeout", "purged_77b"):
        assert secret not in str(shift)
    log = (await client.get(SHIFTS + "/current/log", headers=alice)).json()
    assert [e["seq"] for e in log] == [0] and log[0]["command"] == "start"
    assert "NIGHTSHIFT" in log[0]["events"][0]["text"]


async def test_cannot_start_a_second_shift_until_the_first_ends(client, make_user):
    alice = await make_user()
    first = await _start(client, alice)

    assert (await client.post(SHIFTS + "/", headers=alice)).status_code == 409

    await _cmd(client, alice, "clockout")
    second = await _start(client, alice)
    assert second["id"] != first["id"]
    assert (await client.get(SHIFTS + "/current", headers=alice)).json()["id"] == second["id"]


async def test_read_then_execute_changes_the_persisted_state(client, make_user):
    alice = await make_user()
    await _start(client, alice)

    read = await _cmd(client, alice, "read order-773")
    opened = next(m for m in read["shift"]["view"]["inbox"] if m["id"] == "order-773")
    assert read["accepted"] and opened["body"] and "execute" in [v["verb"] for v in opened["verbs"]]

    done = await _cmd(client, alice, "execute order-773")
    metrics = done["shift"]["view"]["metrics"]
    assert (metrics["technical"], metrics["ethical"], metrics["political"]) == (53, 40, 60)
    assert "Ethical -10" in done["events"][0]["text"]
    assert "order-773" not in [m["id"] for m in done["shift"]["view"]["inbox"]]

    reloaded = (await client.get(SHIFTS + "/current", headers=alice)).json()["view"]
    assert reloaded["metrics"] == metrics and reloaded["clock"] == 7


async def test_rejected_commands_answer_200_change_nothing_and_are_logged(client, make_user):
    alice = await make_user()
    before = (await _start(client, alice))["view"]

    result = await _cmd(client, alice, "execute order-773")  # not read yet

    assert result["accepted"] is False and result["events"][0]["kind"] == "error"
    assert result["shift"]["view"] == before
    log = (await client.get(SHIFTS + "/current/log", headers=alice)).json()
    assert [(e["seq"], e["command"], e["accepted"]) for e in log] == [
        (0, "start", True),
        (1, "execute order-773", False),
    ]


async def test_unannounced_and_nonexistent_messages_are_indistinguishable(client, make_user):
    alice = await make_user()
    await _start(client, alice)  # intel-401 exists but arrives at minute 20

    early = await _cmd(client, alice, "read intel-401")
    missing = await _cmd(client, alice, "read intel-999")

    assert early["accepted"] is False and missing["accepted"] is False
    assert early["events"][0]["text"].replace("intel-401", "X") == missing["events"][0]["text"].replace("intel-999", "X")


async def test_log_replays_oldest_first_and_respects_limit(client, make_user):
    alice = await make_user()
    await _start(client, alice)
    for command in ("status", "inbox", "help"):
        await _cmd(client, alice, command)

    log = (await client.get(SHIFTS + "/current/log?limit=2", headers=alice)).json()

    assert [e["command"] for e in log] == ["inbox", "help"]
    assert (await client.get(SHIFTS + "/current/log?limit=0", headers=alice)).status_code == 422
    assert (await client.get(SHIFTS + "/current/log?limit=501", headers=alice)).status_code == 422


async def test_players_cannot_see_or_affect_each_others_shifts(client, make_user):
    alice = await make_user()
    bob = await make_user()
    await _start(client, alice)

    assert (await client.get(SHIFTS + "/current", headers=bob)).status_code == 404
    await _start(client, bob)
    await _cmd(client, bob, "clockout")

    alice_view = (await client.get(SHIFTS + "/current", headers=alice)).json()["view"]
    assert alice_view["ending"] is None and alice_view["clock"] == 0


@pytest.mark.parametrize("command", ["", "x" * 201])
async def test_command_length_is_validated(client, make_user, command):
    alice = await make_user()
    await _start(client, alice)

    response = await client.post(SHIFTS + "/current/commands", json={"command": command}, headers=alice)

    assert response.status_code == 422


async def test_extra_body_fields_cannot_set_state(client, make_user):
    alice = await make_user()
    await _start(client, alice)

    response = await client.post(
        SHIFTS + "/current/commands",
        json={"command": "status", "technical": 100, "state": {"ethical": 100}},
        headers=alice,
    )

    assert response.status_code == 200
    assert response.json()["shift"]["view"]["metrics"]["technical"] == 50


async def test_a_full_shift_ends_with_an_ending_and_then_rejects_commands(client, make_user):
    alice = await make_user()
    await _start(client, alice)
    await _cmd(client, alice, "read order-773")
    await _cmd(client, alice, "execute order-773")
    result = None
    for _ in range(9):
        result = await _cmd(client, alice, "wait 60")
        if result["shift"]["view"]["ending"]:
            break

    ending = result["shift"]["view"]["ending"]
    assert ending["id"] == "routine-maintenance"
    assert result["events"][-1]["kind"] == "ending"
    after = await _cmd(client, alice, "status")
    assert after["accepted"] is False and "over" in after["events"][0]["text"]
    assert (await client.get(SHIFTS + "/current", headers=alice)).json()["view"]["ending"]["id"] == ending["id"]


async def test_a_stale_write_is_refused_instead_of_overwriting(client, make_user, session_maker):
    await make_user()
    async with session_maker() as first, session_maker() as second:
        user = (await first.execute(select(User))).scalar_one()
        started = await service.start_shift(first, user)
        # Two requests read the same shift (version 0) at the same time...
        winner = await service.get_current_shift(second, user)
        loser = started

        await service.run_command(second, winner, "wait 10")  # ...and one of them commits first.

        with pytest.raises(service.StaleShift):
            await service.run_command(first, loser, "wait 20")

    async with session_maker() as check:
        stored = (await check.execute(select(Shift))).scalar_one()
        assert stored.state["clock"] == 10 and stored.version == 1


async def test_database_itself_allows_only_one_unfinished_shift_per_user(client, make_user, session_maker):
    from sqlalchemy.exc import IntegrityError

    await make_user()
    async with session_maker() as session:
        user = (await session.execute(select(User))).scalar_one()
        session.add(Shift(user_id=user.id, state={}))
        await session.commit()
        session.add(Shift(user_id=user.id, state={}))

        with pytest.raises(IntegrityError):
            await session.commit()
