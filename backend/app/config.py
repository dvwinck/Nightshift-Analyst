"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/nightshift_analyst"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application
    APP_NAME: str = "Nightshift Analyst"
    APP_VERSION: str = "0.1.0"
    #: Development switch: verbose errors, and reset/verify tokens are logged (there is no email
    #: delivery yet). Off by default so a forgotten setting is the safe one.
    DEBUG: bool = False
    #: Echo every SQL statement (including bound parameters) to the log.
    SQL_ECHO: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    @model_validator(mode="after")
    def _reject_weak_secrets_outside_debug(self) -> "Settings":
        """A copy-pasted ``.env.example`` must not reach production with publicly known keys."""
        if self.DEBUG:
            return self
        for name in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = getattr(self, name)
            if len(value) < MIN_SECRET_LENGTH or "change-in-production" in value or value.startswith("your-"):
                raise ValueError(
                    "%s is a placeholder or shorter than %d characters; set a real secret "
                    "(or DEBUG=true for local development)." % (name, MIN_SECRET_LENGTH)
                )
        return self

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
