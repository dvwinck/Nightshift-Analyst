"""Shared fixtures: an in-memory SQLite database and an authenticated HTTP client factory."""

import os
from itertools import count
from typing import Awaitable, Callable, Dict

os.environ.setdefault("SECRET_KEY", "pytest-only-secret-key-0123456789abcdef")
os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-jwt-secret-0123456789abcdef")

import httpx
import pytest_asyncio
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers every table on SQLModel.metadata)
from app.database import get_session
from app.main import app
from app.models.user import User

Headers = Dict[str, str]
MakeUser = Callable[..., Awaitable[Headers]]


#: Point this at a real PostgreSQL (``postgresql+asyncpg://...``) to run the whole suite against it.
#: Without it the tests use an in-memory SQLite database and need no services.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def session_maker():
    if TEST_DATABASE_URL:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    else:
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_maker):
    async def override_get_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def make_user(client, session_maker) -> MakeUser:
    """Register a user, log in, and return its ``Authorization`` headers."""
    counter = count(1)

    async def _make_user(superuser: bool = False) -> Headers:
        n = next(counter)
        email = f"user{n}@example.com"
        password = "correct-horse-battery"
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "username": f"user{n}", "password": password},
        )
        assert response.status_code == 201, response.text
        if superuser:
            async with session_maker() as session:
                await session.execute(
                    update(User).where(User.email == email).values(is_superuser=True)
                )
                await session.commit()
        response = await client.post(
            "/api/v1/auth/jwt/login", data={"username": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _make_user
