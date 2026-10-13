"""Authentication backend configuration."""

from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from app.config import settings


bearer_transport = BearerTransport(
    tokenUrl=f"{settings.API_V1_PREFIX.lstrip('/')}/auth/jwt/login"
)


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy."""
    return JWTStrategy(
        secret=settings.JWT_SECRET_KEY,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
