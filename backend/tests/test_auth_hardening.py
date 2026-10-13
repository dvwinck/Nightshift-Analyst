from loguru import logger

from app.auth.manager import UserManager
from app.config import settings


async def test_swagger_token_url_matches_the_real_login_route(client):
    spec = (await client.get("/openapi.json")).json()

    flows = spec["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]

    assert flows["password"]["tokenUrl"] == "api/v1/auth/jwt/login"


async def test_reset_and_verify_tokens_are_not_logged_outside_debug(monkeypatch, capsys):
    monkeypatch.setattr(settings, "DEBUG", False)
    captured = []
    sink_id = logger.add(captured.append, format="{message}")
    try:
        manager = UserManager(user_db=None)
        user = type("U", (), {"id": "abc"})()
        await manager.on_after_forgot_password(user, token="SECRET-TOKEN")
        await manager.on_after_request_verify(user, token="SECRET-TOKEN")
    finally:
        logger.remove(sink_id)

    everything = "".join(str(m) for m in captured) + capsys.readouterr().out
    assert "SECRET-TOKEN" not in everything


async def test_reset_token_is_logged_in_debug_so_developers_can_reset_passwords(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    captured = []
    sink_id = logger.add(captured.append, format="{message}", level="DEBUG")
    try:
        manager = UserManager(user_db=None)
        user = type("U", (), {"id": "abc"})()
        await manager.on_after_forgot_password(user, token="DEV-TOKEN")
    finally:
        logger.remove(sink_id)

    assert "DEV-TOKEN" in "".join(str(m) for m in captured)
