import pytest
from pydantic import ValidationError

from app.config import MIN_SECRET_LENGTH, Settings

STRONG = "s" * MIN_SECRET_LENGTH


def _settings(**values):
    return Settings(_env_file=None, **values)


def test_debug_is_off_by_default():
    assert _settings(SECRET_KEY=STRONG, JWT_SECRET_KEY=STRONG).DEBUG is False


@pytest.mark.parametrize(
    "secret",
    ["short", "your-secret-key-here-" + "x" * 40, "a" * 40 + "-change-in-production"],
)
def test_weak_or_placeholder_secrets_are_refused_when_debug_is_off(secret):
    with pytest.raises(ValidationError, match="placeholder or shorter"):
        _settings(SECRET_KEY=secret, JWT_SECRET_KEY=STRONG)
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _settings(SECRET_KEY=STRONG, JWT_SECRET_KEY=secret)


def test_placeholders_are_allowed_for_local_development():
    settings = _settings(SECRET_KEY="your-secret-key-here-change-in-production", JWT_SECRET_KEY="x", DEBUG=True)

    assert settings.DEBUG is True


def test_real_secrets_pass_in_production_mode():
    assert _settings(SECRET_KEY=STRONG, JWT_SECRET_KEY=STRONG, DEBUG=False).DEBUG is False
