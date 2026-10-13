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
