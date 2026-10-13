import pytest


async def test_register_login_and_me(client, make_user):
    headers = await make_user()

    response = await client.get("/api/v1/auth/users/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user1@example.com"
    assert body["username"] == "user1"
    assert "hashed_password" not in body


async def test_protected_route_requires_token(client):
    response = await client.get("/api/v1/auth/users/me")

    assert response.status_code == 401


async def test_duplicate_username_is_a_400_not_a_server_error(client, make_user):
    await make_user()

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "username": "user1",
            "password": "correct-horse-battery",
        },
    )

    assert response.status_code == 400


async def test_username_length_is_validated(client):
    for username in ("ab", "x" * 51):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "len@example.com",
                "username": username,
                "password": "correct-horse-battery",
            },
        )
        assert response.status_code == 422, username


async def test_cannot_rename_to_someone_elses_username(client, make_user):
    await make_user()
    bob = await make_user()

    response = await client.patch(
        "/api/v1/auth/users/me", json={"username": "user1"}, headers=bob
    )

    assert response.status_code == 400


async def test_can_keep_own_username_when_updating_profile(client, make_user):
    alice = await make_user()

    response = await client.patch(
        "/api/v1/auth/users/me", json={"username": "user1"}, headers=alice
    )

    assert response.status_code == 200


async def test_short_passwords_are_rejected_with_a_readable_reason(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "pw@example.com", "username": "pwuser", "password": "short"},
    )

    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"]["reason"]


async def test_usernames_are_unique_regardless_of_case(client, make_user):
    await make_user()  # user1

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "case@example.com", "username": "USER1", "password": "correct-horse-battery"},
    )

    assert response.status_code == 400


async def test_the_database_enforces_case_insensitive_usernames_too(client, make_user, session_maker):
    from sqlalchemy.exc import IntegrityError

    from app.models.user import User

    await make_user()  # user1
    async with session_maker() as session:
        session.add(User(email="db@example.com", username="User1", hashed_password="x"))
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.parametrize(
    "username",
    ["  user9  ", "user\u200b9", "<img src=x>", "has space", "semi;colon", "ünïcode"],
)
async def test_usernames_are_limited_to_a_safe_charset(client, username):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "safe@example.com", "username": username, "password": "correct-horse-battery"},
    )

    assert response.status_code == 422


async def test_enormous_passwords_are_rejected(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "big@example.com", "username": "bigpw", "password": "x" * 129},
    )

    assert response.status_code == 422


async def test_validation_errors_do_not_echo_the_input_back(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "echo@example.com", "username": "<b>secret-marker</b>", "password": "correct-horse-battery"},
    )

    assert response.status_code == 422
    assert "secret-marker" not in response.text
    assert response.json()["detail"][0]["loc"][-1] == "username"
