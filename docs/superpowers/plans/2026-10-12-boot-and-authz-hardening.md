# Boot & Authorization Hardening Implementation Plan

> **STATUS (read this first): partly superseded.** Decision D1 was resolved in favour of the GDD, so the
> detective domain (cases / characters / game state) was **removed** instead of hardened.
> **Done as written:** Task 1 (boot fix + harness), Task 2 (auth hardening) and Task 6 steps 1-6 (frontend build fix).
> **Deliberately not done:** Tasks 3, 4, 5 and Task 6 steps 7-9, Task 7's merge step: their subject no longer exists.
> The work lives on branch `feat/shift-engine`, not `fix/boot-and-authz-hardening`. The server-authority
> principles of Tasks 3-5 were applied to the new `/shifts` API instead (see the roadmap).
> Later reviews added to Task 2's scope: password >= 8 and <= 128 chars, safe-charset case-insensitive usernames,
> and `pydantic==2.13.5` is pinned in `requirements.txt`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backend actually start, give it a real test suite, close every cross-user access and client-writable-outcome hole found in the analysis, and make the frontend build and match the new API.

**Architecture:** `User` becomes a plain SQLAlchemy declarative model sharing `SQLModel.metadata` (fastapi-users cannot be mixed into a SQLModel table). Routes stop trusting ownership and outcomes from the request body: the owner comes from the JWT, ownership of a case is enforced by one shared dependency (`get_owned_case`), characters are superuser-authored content whose solution flag is never serialized, and game state is created server-side with defaults and never patched by the client. Tests use httpx `ASGITransport` against in-memory SQLite by overriding `get_session`.

**Tech Stack:** FastAPI 0.120.4, SQLModel 0.0.27, fastapi-users 14.0.2, pytest 8.4.2 + pytest-asyncio 1.2.0 + httpx 0.28.1 + aiosqlite 0.22.1, Vite/React/TypeScript.

**Spec:** `docs/superpowers/plans/2026-10-12-improvement-roadmap.md` (findings F1–F7 and principles in §4). This plan is safe under either answer to decision D1 in that document.

## Global Constraints

- Python 3.9-compatible syntax only (Dockerfile is `python:3.9-slim`): `Optional[X]`, never `X | None`; no `match`.
- Work on branch `fix/boot-and-authz-hardening` cut from `main` (this repo has no `base` branch). **Do not push and do not open a PR.** Merge locally only (Task 7).
- Players never write: owner ids, rewards, stress impact, clue counts, case progress/status, character suspicion/trust, or any game-state value.
- Another user's resource and a nonexistent resource are indistinguishable: both return **404**, never 403. 403 is only for an authenticated non-superuser attempting an authoring action.
- Backend tests must run with no Postgres/Redis/Docker: in-memory SQLite only.
- Exact new pins in `backend/requirements.txt`: `aiosqlite==0.22.1`, `pytest-asyncio==1.2.0`.
- Lint must not get worse than baseline: `ruff check app tests` ≤ 4 errors (3 are pre-existing `F821` forward references in `models/`). Making lint green is Plan 2.
- Commit after every task; messages use `fix:`, `test:`, `docs:` prefixes.

## Review Focus

Inputs the analysis implies but that are easy to forget; each has a test in the task that owns the code.

1. Malformed UUID in a path (`/cases/not-a-uuid`) → 422, not 500 (Task 3).
2. A deactivated user holding a still-valid JWT → 401 (Task 3).
3. Registering/renaming to an existing username → 400, while keeping your own username on a profile update stays 200 (Task 2).
4. Username shorter than 3 or longer than 50 → 422 (SQLite would accept 80 chars; Postgres would 500) (Task 2).
5. A second `POST /game-state/` → 409, and unexpected body fields (`user_id`, `reputation`) are ignored (Task 5); a stranger's character id answers exactly like a missing one (Task 4).

## File Structure

| File | Responsibility |
|---|---|
| `backend/requirements.txt` (modify) | add test-only pins |
| `backend/pytest.ini` (create) | asyncio mode, `pythonpath = .` |
| `backend/tests/conftest.py` (create) | SQLite engine, `client`, `make_user` fixtures |
| `backend/tests/test_auth_smoke.py` (create) | register/login/me + username rules |
| `backend/tests/test_auth_hardening.py` (create) | Swagger tokenUrl, token logging |
| `backend/tests/test_cases_authz.py` (create) | case ownership + server-owned fields |
| `backend/tests/test_characters_authz.py` (create) | character authoring/visibility |
| `backend/tests/test_game_state.py` (create) | game-state lifecycle, no client writes |
| `backend/app/models/user.py` (modify) | declarative `User` + fastapi-users schemas |
| `backend/app/auth/manager.py` (modify) | username uniqueness → 400; safe logging |
| `backend/app/auth/backend.py` (modify) | correct Swagger `tokenUrl` |
| `backend/app/auth/users.py` (modify) | add `current_superuser` |
| `backend/app/api/deps.py` (create) | `get_owned_case` shared dependency |
| `backend/app/models/{case,character,game_state}.py`, `models/__init__.py` (modify) | narrow create/read/update schemas |
| `backend/app/api/v1/routes/{cases,characters,game_state}.py` (modify) | rewritten routes |
| `frontend/tsconfig.node.json`, `frontend/src/api/client.ts` (modify) | make `npm run build` pass |
| `frontend/src/{types/index.ts,api/cases.ts,components/CaseForm.tsx,pages/DashboardPage.tsx}` (modify) | match the narrowed API |
| `CLAUDE.md`, `backend/README.md` (modify) | document the new reality |

---

### Task 1: Make the backend boot and add the test harness

**Files:**
- Modify: `backend/requirements.txt`, `backend/app/models/user.py`
- Create: `backend/pytest.ini`, `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_auth_smoke.py`

**Interfaces:**
- Produces: fixtures `session_maker`, `client` (httpx `AsyncClient` with `get_session` overridden), and `make_user(superuser: bool = False) -> Dict[str, str]` returning `{"Authorization": "Bearer …"}`. Users are `user1@example.com`/`user1`, `user2@…`, … in creation order, password `correct-horse-battery`. Every later task relies on these names.
- Produces: `app.models.user.{Base, User, UserRead, UserCreate, UserUpdate}`.

- [ ] **Step 1: Branch and commit the docs**

```bash
cd /Users/diogo/projects/Nightshift-Analyst
git checkout main
git status --short        # expect only: ?? CLAUDE.md  and  ?? docs/
git checkout -b fix/boot-and-authz-hardening
git add CLAUDE.md docs/superpowers/plans
git commit -m "docs: add CLAUDE.md and improvement plans"
```

- [ ] **Step 2: Add test dependencies and create the venv**

Append to `backend/requirements.txt`:

```
aiosqlite==0.22.1
pytest-asyncio==1.2.0
```

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

(`venv/` is already in `backend/.gitignore`. Any Python 3.9–3.12 works; the Dockerfile uses 3.9.)

- [ ] **Step 3: Write the harness and smoke tests**

`backend/pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
pythonpath = .
testpaths = tests
```

`backend/tests/__init__.py`: empty file.

`backend/tests/conftest.py`:

```python
"""Shared fixtures: an in-memory SQLite database and an authenticated HTTP client factory."""

import os
from itertools import count
from typing import Awaitable, Callable, Dict

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")

import httpx
import pytest_asyncio
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers every table on SQLModel.metadata)
from app.database import get_session
from app.main import app
from app.models.user import User

Headers = Dict[str, str]
MakeUser = Callable[..., Awaitable[Headers]]


@pytest_asyncio.fixture
async def session_maker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
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
```

`backend/tests/test_auth_smoke.py`:

```python
async def test_register_login_and_me(client, make_user):
    headers = await make_user()

    response = await client.get("/api/v1/auth/users/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user1@example.com"
    assert body["username"] == "user1"
    assert "hashed_password" not in body


async def test_protected_route_requires_token(client):
    response = await client.get("/api/v1/cases/")

    assert response.status_code == 401
```

- [ ] **Step 4: Run the tests and watch them fail**

Run: `cd backend && pytest -q`
Expected: collection error from `import app.models`, ending in
`pydantic.errors.PydanticSchemaGenerationError: Unable to generate pydantic-core schema for sqlalchemy.orm.base.Mapped[str]` (raised from `app/models/user.py`).

- [ ] **Step 5: Replace `backend/app/models/user.py`**

```python
"""User model.

fastapi-users ships a SQLAlchemy 2.0 declarative table (``Mapped[...]`` columns) which
cannot be mixed into a ``SQLModel`` table class. ``User`` is therefore a plain
declarative model that shares ``SQLModel.metadata``, so the other (SQLModel) tables can
still reference ``users.id`` in their foreign keys and ``create_all`` sees every table.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi_users import schemas
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlmodel import SQLModel


class Base(DeclarativeBase):
    """Declarative base sharing SQLModel's metadata."""

    metadata = SQLModel.metadata


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User database model."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserRead(schemas.BaseUser[UUID]):
    """User read schema."""

    username: str
    created_at: datetime
    updated_at: datetime


class UserCreate(schemas.BaseUserCreate):
    """User creation schema."""

    username: str


class UserUpdate(schemas.BaseUserUpdate):
    """User update schema."""

    username: Optional[str] = None
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `cd backend && pytest -q -p no:warnings`
Expected: `2 passed`.

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/pytest.ini backend/tests backend/app/models/user.py
git commit -m "fix: make backend boot (declarative User) and add pytest harness"
```

---

### Task 2: Registration robustness and auth hardening

**Files:**
- Modify: `backend/app/models/user.py` (full replacement), `backend/app/auth/manager.py` (full replacement), `backend/app/auth/backend.py`
- Test: `backend/tests/test_auth_smoke.py` (append), `backend/tests/test_auth_hardening.py` (create)

**Interfaces:**
- Consumes: `client`, `make_user` from Task 1 (`make_user()` first call is `user1`).
- Produces: `UserManager._ensure_username_is_free(username, owner_id=None)`; duplicate username → `fastapi_users.exceptions.UserAlreadyExists` (HTTP 400). `USERNAME_MIN_LENGTH = 3`, `USERNAME_MAX_LENGTH = 50` in `app.models.user`.

- [ ] **Step 1: Append to `backend/tests/test_auth_smoke.py`**

```python


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
```

- [ ] **Step 2: Create `backend/tests/test_auth_hardening.py`**

```python
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
```

- [ ] **Step 3: Run and watch them fail**

Run: `cd backend && pytest -q -p no:warnings tests/test_auth_smoke.py tests/test_auth_hardening.py`
Expected: FAIL — `sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: users.username` (duplicate register and rename), `assert 201 == 422` for the 51-char username, `'auth/login' == 'api/v1/auth/jwt/login'`, and both token-logging tests. `test_can_keep_own_username_when_updating_profile` already passes (regression guard).

- [ ] **Step 4: Replace `backend/app/models/user.py`**

```python
"""User model.

fastapi-users ships a SQLAlchemy 2.0 declarative table (``Mapped[...]`` columns) which
cannot be mixed into a ``SQLModel`` table class. ``User`` is therefore a plain
declarative model that shares ``SQLModel.metadata``, so the other (SQLModel) tables can
still reference ``users.id`` in their foreign keys and ``create_all`` sees every table.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi_users import schemas
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from pydantic import Field
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlmodel import SQLModel

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 50


class Base(DeclarativeBase):
    """Declarative base sharing SQLModel's metadata."""

    metadata = SQLModel.metadata


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User database model."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(USERNAME_MAX_LENGTH), unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserRead(schemas.BaseUser[UUID]):
    """User read schema."""

    username: str
    created_at: datetime
    updated_at: datetime


class UserCreate(schemas.BaseUserCreate):
    """User creation schema."""

    username: str = Field(min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH)


class UserUpdate(schemas.BaseUserUpdate):
    """User update schema."""

    username: Optional[str] = Field(
        default=None, min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
```

- [ ] **Step 5: Replace `backend/app/auth/manager.py`**

```python
"""User manager for authentication."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions, schemas
from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.auth.database import get_user_db


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """User manager class."""

    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def _ensure_username_is_free(
        self, username: Optional[str], owner_id: Optional[UUID] = None
    ) -> None:
        """Raise ``UserAlreadyExists`` (-> HTTP 400) instead of a raw DB IntegrityError."""
        if username is None:
            return
        result = await self.user_db.session.execute(
            select(User.id).where(User.username == username)
        )
        existing_id = result.scalar_one_or_none()
        if existing_id is not None and existing_id != owner_id:
            raise exceptions.UserAlreadyExists()

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> User:
        await self._ensure_username_is_free(getattr(user_create, "username", None))
        return await super().create(user_create, safe=safe, request=request)

    async def update(
        self,
        user_update: schemas.UU,
        user: User,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> User:
        await self._ensure_username_is_free(
            getattr(user_update, "username", None), owner_id=user.id
        )
        return await super().update(user_update, user, safe=safe, request=request)

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after user registration."""
        logger.info("User {} registered", user.id)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after forgot password request."""
        logger.info("Password reset requested for user {}", user.id)
        if settings.DEBUG:
            logger.debug("Password reset token for user {}: {}", user.id, token)

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after verification request."""
        logger.info("Verification requested for user {}", user.id)
        if settings.DEBUG:
            logger.debug("Verification token for user {}: {}", user.id, token)


async def get_user_manager(user_db=Depends(get_user_db)):
    """Get user manager instance."""
    yield UserManager(user_db)
```

- [ ] **Step 6: Fix the Swagger token URL in `backend/app/auth/backend.py`**

Replace

```python
bearer_transport = BearerTransport(tokenUrl="auth/login")
```

with

```python
bearer_transport = BearerTransport(
    tokenUrl=f"{settings.API_V1_PREFIX.lstrip('/')}/auth/jwt/login"
)
```

- [ ] **Step 7: Run and watch them pass**

Run: `cd backend && pytest -q -p no:warnings`
Expected: `9 passed` (2 from Task 1 + 4 new smoke + 3 hardening).

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/user.py backend/app/auth backend/tests
git commit -m "fix: username uniqueness/length, safe token logging, correct Swagger tokenUrl"
```

---

### Task 3: Cases — owner from the token, server-owned fields, no PATCH

**Files:**
- Create: `backend/app/api/deps.py`, `backend/tests/test_cases_authz.py`
- Modify: `backend/app/models/case.py`, `backend/app/models/__init__.py`, `backend/app/api/v1/routes/cases.py` (full replacement)

**Interfaces:**
- Consumes: `client`, `make_user`, `session_maker` from Task 1.
- Produces: `app.api.deps.get_owned_case(case_id: UUID, session, user) -> Case` (404 when missing or not owned). `CaseCreate` now has only `title: str`, `description: str`, `difficulty: CaseDifficulty`. `CaseUpdate` no longer exists. Task 4 consumes `get_owned_case`.

- [ ] **Step 1: Write `backend/tests/test_cases_authz.py`**

```python
from sqlalchemy import update

from app.models.user import User

CASE = {"title": "Missing journalist", "description": "District 4", "difficulty": "medium"}


async def _create_case(client, headers, **overrides):
    response = await client.post("/api/v1/cases/", json={**CASE, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def test_case_owner_comes_from_the_token_not_the_body(client, make_user):
    alice = await make_user()
    bob = await make_user()
    bob_id = (await client.get("/api/v1/auth/users/me", headers=bob)).json()["id"]
    alice_id = (await client.get("/api/v1/auth/users/me", headers=alice)).json()["id"]

    created = await _create_case(client, alice, user_id=bob_id)

    assert created["user_id"] == alice_id


async def test_client_cannot_choose_rewards_or_progress(client, make_user):
    alice = await make_user()

    created = await _create_case(
        client,
        alice,
        reputation_reward=9999,
        stress_impact=-50,
        total_clues=1,
        clues_found=1,
        status="completed",
    )

    assert created["reputation_reward"] == 20
    assert created["stress_impact"] == 10
    assert created["total_clues"] == 3
    assert created["clues_found"] == 0
    assert created["status"] == "pending"


async def test_other_users_cannot_read_or_delete_a_case(client, make_user):
    alice = await make_user()
    bob = await make_user()
    case = await _create_case(client, alice)

    assert (await client.get(f"/api/v1/cases/{case['id']}", headers=bob)).status_code == 404
    assert (await client.delete(f"/api/v1/cases/{case['id']}", headers=bob)).status_code == 404
    assert (await client.get("/api/v1/cases/", headers=bob)).json() == []
    assert (await client.get(f"/api/v1/cases/{case['id']}", headers=alice)).status_code == 200


async def test_cases_cannot_be_patched_by_players(client, make_user):
    alice = await make_user()
    case = await _create_case(client, alice)

    response = await client.patch(
        f"/api/v1/cases/{case['id']}", json={"status": "completed"}, headers=alice
    )

    assert response.status_code == 405


async def test_malformed_case_id_is_a_422(client, make_user):
    alice = await make_user()

    response = await client.get("/api/v1/cases/not-a-uuid", headers=alice)

    assert response.status_code == 422


async def test_deactivated_user_token_is_rejected(client, make_user, session_maker):
    alice = await make_user()
    async with session_maker() as session:
        await session.execute(update(User).values(is_active=False))
        await session.commit()

    response = await client.get("/api/v1/cases/", headers=alice)

    assert response.status_code == 401
```

- [ ] **Step 2: Run and watch it fail**

Run: `cd backend && pytest -q -p no:warnings tests/test_cases_authz.py`
Expected: the first four tests FAIL — the helper's `assert response.status_code == 201` fails with `422` because the current `CaseCreate` requires `user_id` in the body. (Validated against the original routes.) `test_malformed_case_id_is_a_422` and `test_deactivated_user_token_is_rejected` may pass already; they are regression guards for behavior that must be kept.

- [ ] **Step 3: Create `backend/app/api/deps.py`**

```python
"""Shared route dependencies."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.database import get_session
from app.models.case import Case
from app.models.user import User


async def get_owned_case(
    case_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
) -> Case:
    """Return the case if it belongs to the current user, otherwise 404.

    404 (not 403) so the API does not reveal whether someone else's case exists.
    """
    result = await session.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case
```

- [ ] **Step 4: Narrow the case schemas in `backend/app/models/case.py`**

Replace the `CaseCreate` class:

```python
class CaseCreate(CaseBase):
    """Case creation schema."""

    user_id: UUID
```

with:

```python
class CaseCreate(SQLModel):
    """Case creation schema.

    Players only choose what the case is about. Owner, rewards, stress impact, clue
    counts and progress are decided by the server, never by the client.
    """

    title: str
    description: str
    difficulty: CaseDifficulty
```

Delete the whole `CaseUpdate` class at the bottom of the file.

- [ ] **Step 5: Update `backend/app/models/__init__.py`**

Change the import line to `from app.models.case import Case, CaseCreate, CaseRead` and delete the `"CaseUpdate",` entry from `__all__`.

- [ ] **Step 6: Replace `backend/app/api/v1/routes/cases.py`**

```python
"""Case management routes."""

from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_case
from app.auth.users import current_active_user
from app.database import get_session
from app.models.case import Case, CaseCreate, CaseRead
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Create a case owned by the current user."""
    case = Case(**case_data.model_dump(), user_id=user.id)
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


@router.get("/", response_model=List[CaseRead])
async def list_cases(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """List the current user's cases."""
    result = await session.execute(select(Case).where(Case.user_id == user.id))
    return result.scalars().all()


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(case: Case = Depends(get_owned_case)):
    """Get one of the current user's cases."""
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case: Case = Depends(get_owned_case),
    session: AsyncSession = Depends(get_session),
):
    """Delete one of the current user's cases."""
    await session.delete(case)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 7: Run and watch it pass**

Run: `cd backend && pytest -q -p no:warnings tests/test_cases_authz.py`
Expected: `6 passed`.

- [ ] **Step 8: Prove the tests guard the filter (mutation check, then restore)**

```bash
cd backend
cp app/api/deps.py app/api/deps.py.bak
sed -i.orig 's/select(Case).where(Case.id == case_id, Case.user_id == user.id)/select(Case).where(Case.id == case_id)/' app/api/deps.py
pytest -q -p no:warnings tests/test_cases_authz.py   # expected: test_other_users_cannot_read_or_delete_a_case FAILS
mv app/api/deps.py.bak app/api/deps.py && rm -f app/api/deps.py.orig
pytest -q -p no:warnings tests/test_cases_authz.py   # expected: 6 passed
git status --short                                   # expected: no *.bak / *.orig files listed
```

(During validation this mutation also failed `test_other_users_cannot_see_a_cases_characters`, which exists from Task 4 on.)

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/deps.py backend/app/models backend/app/api/v1/routes/cases.py backend/tests/test_cases_authz.py
git commit -m "fix: cases are owned via the token, server owns rewards/progress, drop PATCH"
```

---

### Task 4: Characters — authored by superusers, visible to the case owner, solution never serialized

**Files:**
- Modify: `backend/app/auth/users.py`, `backend/app/models/character.py`, `backend/app/models/__init__.py`, `backend/app/api/v1/routes/characters.py` (full replacement)
- Test: `backend/tests/test_characters_authz.py`

**Interfaces:**
- Consumes: `get_owned_case` (Task 3), `make_user(superuser=True)` (Task 1).
- Produces: `app.auth.users.current_superuser` (FastAPI dependency; 403 for non-superusers, 401 anonymous). `CharacterRead` has **no** `is_guilty`. `CharacterUpdate` no longer exists.

- [ ] **Step 1: Write `backend/tests/test_characters_authz.py`**

```python
async def _make_case(client, headers):
    response = await client.post(
        "/api/v1/cases/",
        json={"title": "Case", "description": "d", "difficulty": "easy"},
        headers=headers,
    )
    return response.json()["id"]


def _character(case_id, **overrides):
    return {
        "case_id": case_id,
        "name": "Vera Holt",
        "role": "suspect",
        "description": "Night clerk",
        "personality_traits": "[]",
        "is_guilty": True,
        **overrides,
    }


async def test_players_cannot_create_characters(client, make_user):
    alice = await make_user()
    case_id = await _make_case(client, alice)

    response = await client.post("/api/v1/characters/", json=_character(case_id), headers=alice)

    assert response.status_code == 403


async def test_character_for_missing_case_is_rejected(client, make_user):
    admin = await make_user(superuser=True)

    response = await client.post(
        "/api/v1/characters/",
        json=_character("00000000-0000-0000-0000-000000000000"),
        headers=admin,
    )

    assert response.status_code == 404


async def test_owner_reads_characters_without_the_culprit_flag(client, make_user):
    admin = await make_user(superuser=True)
    alice = await make_user()
    case_id = await _make_case(client, alice)
    created = await client.post("/api/v1/characters/", json=_character(case_id), headers=admin)
    assert created.status_code == 201, created.text
    assert "is_guilty" not in created.json()

    listed = await client.get(f"/api/v1/characters/case/{case_id}", headers=alice)
    single = await client.get(f"/api/v1/characters/{created.json()['id']}", headers=alice)

    assert listed.status_code == 200 and len(listed.json()) == 1
    assert "is_guilty" not in listed.json()[0]
    assert single.status_code == 200 and "is_guilty" not in single.json()


async def test_other_users_cannot_see_a_cases_characters(client, make_user):
    admin = await make_user(superuser=True)
    alice = await make_user()
    bob = await make_user()
    case_id = await _make_case(client, alice)
    created = await client.post("/api/v1/characters/", json=_character(case_id), headers=admin)
    character_id = created.json()["id"]

    assert (await client.get(f"/api/v1/characters/case/{case_id}", headers=bob)).status_code == 404
    assert (await client.get(f"/api/v1/characters/{character_id}", headers=bob)).status_code == 404


async def test_players_cannot_patch_or_delete_characters(client, make_user):
    admin = await make_user(superuser=True)
    alice = await make_user()
    case_id = await _make_case(client, alice)
    created = await client.post("/api/v1/characters/", json=_character(case_id), headers=admin)
    character_id = created.json()["id"]

    patch = await client.patch(
        f"/api/v1/characters/{character_id}", json={"suspicion_level": 100}, headers=alice
    )
    delete = await client.delete(f"/api/v1/characters/{character_id}", headers=alice)

    assert patch.status_code == 405
    assert delete.status_code == 403
```

- [ ] **Step 2: Run and watch it fail**

Run: `cd backend && pytest -q -p no:warnings tests/test_characters_authz.py`
Expected: 5 FAIL on status-code/field assertions (the old routes let any user create characters, accept a nonexistent `case_id`, return `is_guilty`, serve strangers, and route PATCH). The exact messages were validated against the original routes only up to the case-creation step, so judge by "fails for those reasons", not by exact text.

- [ ] **Step 3: Add `current_superuser` to `backend/app/auth/users.py`**

Append after `current_active_user = …`:

```python
current_superuser = fastapi_users.current_user(active=True, superuser=True)
```

- [ ] **Step 4: Edit `backend/app/models/character.py`**

Replace the `CharacterRead` class with:

```python
class CharacterRead(SQLModel):
    """Character read schema.

    Deliberately omits ``is_guilty``: the answer to the mystery must never reach the client.
    """

    id: UUID
    case_id: UUID
    name: str
    role: CharacterRole
    description: str
    personality_traits: str
    suspicion_level: int
    trust_level: int
    dialogue_history: Optional[str]
    testimony: Optional[str]
    alibi: Optional[str]
    created_at: datetime
    updated_at: datetime
```

Delete the `CharacterUpdate` class at the bottom of the file.

- [ ] **Step 5: Update `backend/app/models/__init__.py`**

Change to `from app.models.character import Character, CharacterCreate, CharacterRead` and delete the `"CharacterUpdate",` entry from `__all__`.

- [ ] **Step 6: Replace `backend/app/api/v1/routes/characters.py`**

```python
"""Character routes.

Characters are authored content: only superusers create or delete them, and players only
read the characters of cases they own. Suspicion/trust change through game commands, never
through a client-writable PATCH.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_case
from app.auth.users import current_active_user, current_superuser
from app.database import get_session
from app.models.case import Case
from app.models.character import Character, CharacterCreate, CharacterRead
from app.models.user import User

router = APIRouter()


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")


@router.post("/", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(
    character_data: CharacterCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_superuser),
):
    """Create a character for an existing case (superusers only)."""
    if await session.get(Case, character_data.case_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    character = Character(**character_data.model_dump())
    session.add(character)
    await session.commit()
    await session.refresh(character)
    return character


@router.get("/case/{case_id}", response_model=List[CharacterRead])
async def list_case_characters(
    case: Case = Depends(get_owned_case),
    session: AsyncSession = Depends(get_session),
):
    """List the characters of one of the current user's cases."""
    result = await session.execute(select(Character).where(Character.case_id == case.id))
    return result.scalars().all()


@router.get("/{character_id}", response_model=CharacterRead)
async def get_character(
    character_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Get a character, only if its case belongs to the current user."""
    result = await session.execute(
        select(Character)
        .join(Case, Case.id == Character.case_id)
        .where(Character.id == character_id, Case.user_id == user.id)
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise _not_found()
    return character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_superuser),
):
    """Delete a character (superusers only)."""
    character = await session.get(Character, character_id)
    if character is None:
        raise _not_found()
    await session.delete(character)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 7: Run and watch it pass**

Run: `cd backend && pytest -q -p no:warnings`
Expected: `20 passed` (2 + 7 from Tasks 1–2, plus 6 from Task 3, plus 5 from this task).

- [ ] **Step 8: Commit**

```bash
git add backend/app/auth/users.py backend/app/models backend/app/api/v1/routes/characters.py backend/tests/test_characters_authz.py
git commit -m "fix: characters are superuser-authored, owner-visible, and never expose is_guilty"
```

---

### Task 5: Game state — server-created, never client-written

**Files:**
- Modify: `backend/app/models/game_state.py`, `backend/app/models/__init__.py`, `backend/app/api/v1/routes/game_state.py` (full replacement)
- Test: `backend/tests/test_game_state.py`

**Interfaces:**
- Consumes: `client`, `make_user`.
- Produces: `POST /game-state/` takes **no body**, returns 201 with defaults (`current_day=1, stress_level=0, reputation=50`), 409 if one already exists. `GameStateCreate` and `GameStateUpdate` no longer exist. Plan 3's engine becomes the only writer.

- [ ] **Step 1: Write `backend/tests/test_game_state.py`**

```python
async def test_game_state_lifecycle(client, make_user):
    alice = await make_user()
    me = (await client.get("/api/v1/auth/users/me", headers=alice)).json()

    assert (await client.get("/api/v1/game-state/me", headers=alice)).status_code == 404

    created = await client.post("/api/v1/game-state/", headers=alice)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["user_id"] == me["id"]
    assert (body["current_day"], body["stress_level"], body["reputation"]) == (1, 0, 50)

    assert (await client.post("/api/v1/game-state/", headers=alice)).status_code == 409
    assert (await client.get("/api/v1/game-state/me", headers=alice)).status_code == 200
    assert (await client.delete("/api/v1/game-state/me", headers=alice)).status_code == 204
    assert (await client.get("/api/v1/game-state/me", headers=alice)).status_code == 404


async def test_game_state_ignores_client_supplied_values(client, make_user):
    alice = await make_user()
    bob = await make_user()
    bob_id = (await client.get("/api/v1/auth/users/me", headers=bob)).json()["id"]

    created = await client.post(
        "/api/v1/game-state/",
        json={"user_id": bob_id, "reputation": 100, "cases_solved": 999},
        headers=alice,
    )

    assert created.status_code == 201
    assert created.json()["user_id"] != bob_id
    assert created.json()["reputation"] == 50
    assert created.json()["cases_solved"] == 0
    assert (await client.get("/api/v1/game-state/me", headers=bob)).status_code == 404


async def test_players_cannot_patch_game_state(client, make_user):
    alice = await make_user()
    await client.post("/api/v1/game-state/", headers=alice)

    response = await client.patch(
        "/api/v1/game-state/me", json={"cases_solved": 999}, headers=alice
    )

    assert response.status_code == 405
```

- [ ] **Step 2: Run and watch it fail**

Run: `cd backend && pytest -q -p no:warnings tests/test_game_state.py`
Expected: 3 FAIL — `POST` without a body returns 422 (the old route requires a `GameStateCreate` body), and PATCH is not answered with 405.

- [ ] **Step 3: Edit `backend/app/models/game_state.py`**

Delete these two classes entirely (leave `GameStateBase`, `GameState`, `GameStateRead` untouched):

```python
class GameStateCreate(GameStateBase):
    """Game state creation schema."""

    user_id: UUID
```

and the trailing `GameStateUpdate(SQLModel)` class (all of its `Optional[...] = None` fields).

- [ ] **Step 4: Update `backend/app/models/__init__.py`**

Change to `from app.models.game_state import GameState, GameStateRead` and delete the `"GameStateCreate",` and `"GameStateUpdate",` entries from `__all__`.

- [ ] **Step 5: Replace `backend/app/api/v1/routes/game_state.py`**

```python
"""Game state routes.

The client never writes game state: it is created with server defaults here and changed
only by server-side game logic.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.database import get_session
from app.models.game_state import GameState, GameStateRead
from app.models.user import User

router = APIRouter()


async def _get_own_game_state(session: AsyncSession, user: User) -> GameState:
    result = await session.execute(select(GameState).where(GameState.user_id == user.id))
    game_state = result.scalar_one_or_none()
    if game_state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game state not found")
    return game_state


@router.post("/", response_model=GameStateRead, status_code=status.HTTP_201_CREATED)
async def create_game_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Start a new game for the current user, with default values."""
    session.add(GameState(user_id=user.id))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Game state already exists"
        )
    return await _get_own_game_state(session, user)


@router.get("/me", response_model=GameStateRead)
async def get_my_game_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Get the current user's game state."""
    return await _get_own_game_state(session, user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_game_state(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
):
    """Reset progress by deleting the current user's game state."""
    await session.delete(await _get_own_game_state(session, user))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 6: Run the whole backend suite**

Run: `cd backend && pytest -q -p no:warnings`
Expected: `23 passed` (9 + 6 + 5 + 3).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models backend/app/api/v1/routes/game_state.py backend/tests/test_game_state.py
git commit -m "fix: game state is server-created with defaults and never client-patched"
```

---

### Task 6: Frontend — make `npm run build` pass and match the narrowed API

**Files:**
- Modify: `frontend/tsconfig.node.json` (full replacement), `frontend/src/api/client.ts`, `frontend/src/types/index.ts`, `frontend/src/api/cases.ts`, `frontend/src/components/CaseForm.tsx` (full replacement), `frontend/src/pages/DashboardPage.tsx`

**Interfaces:**
- Consumes: the new `POST /cases/` contract (`title`, `description`, `difficulty` only).
- Produces: `CaseCreatePayload = Pick<Case, "title" | "description" | "difficulty">`; `CaseForm` props are `{ onCreate, isSubmitting? }` (no `userId`); `updateCase`/`CaseUpdatePayload` are removed (nothing used them).

- [ ] **Step 1: Confirm the baseline build is broken**

Run: `cd frontend && npm ci && npm run build`
Expected: FAIL — `tsconfig.json(20,18): error TS6310: Referenced project … may not disable emit.` plus ~108 errors such as `Cannot find name 'Set'` from `node_modules/vite/...`.

- [ ] **Step 2: Replace `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "target": "ES2020",
    "lib": ["ES2020"],
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "emitDeclarationOnly": true,
    "outDir": "./node_modules/.tmp/tsconfig-node"
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Run the build again**

Run: `cd frontend && npm run build`
Expected: FAIL with exactly one remaining error: `src/api/client.ts(44,42): error TS2358: The left-hand side of an 'instanceof' expression must be of type 'any', an object type or a type parameter.`

- [ ] **Step 4: Fix the narrowing bug in `frontend/src/api/client.ts`**

Replace

```ts
  if (body instanceof URLSearchParams || body instanceof FormData) {
    requestBody = body;
  } else if (body && typeof body === "object") {
    fetchHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  } else if (typeof body === "string" || body instanceof Blob) {
    requestBody = body;
  }
```

with

```ts
  if (
    typeof body === "string" ||
    body instanceof URLSearchParams ||
    body instanceof FormData ||
    body instanceof Blob
  ) {
    requestBody = body;
  } else if (body && typeof body === "object") {
    fetchHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }
```

- [ ] **Step 5: Run the build**

Run: `cd frontend && npm run build`
Expected: PASS (`✓ built in …ms`).

- [ ] **Step 6: Commit the build fix on its own**

```bash
git add frontend/tsconfig.node.json frontend/src/api/client.ts
git commit -m "fix(frontend): make npm run build pass"
```

- [ ] **Step 7: Align types, API client, form and page with the narrowed API**

In `frontend/src/types/index.ts`, replace everything from `export type CaseCreatePayload = {` to the end of the file with:

```ts
// Players only choose what a case is about; the server owns the owner, rewards and progress.
export type CaseCreatePayload = Pick<Case, "title" | "description" | "difficulty">;
```

In `frontend/src/api/cases.ts`: change the import to `import { Case, CaseCreatePayload } from "../types";` and delete the whole `updateCase` function (the last function in the file).

In `frontend/src/pages/DashboardPage.tsx`: change `const { token, user } = useAuth();` to `const { token } = useAuth();` and replace

```tsx
      {user && (
        <CaseForm userId={user.id} onCreate={handleCreate} isSubmitting={isCreating} />
      )}
```

with

```tsx
      <CaseForm onCreate={handleCreate} isSubmitting={isCreating} />
```

Replace `frontend/src/components/CaseForm.tsx` with:

```tsx
import { FormEvent, useState } from "react";

import { CaseCreatePayload, CaseDifficulty } from "../types";

const difficulties: CaseDifficulty[] = ["easy", "medium", "hard", "extreme"];

type CaseFormProps = {
  onCreate: (payload: CaseCreatePayload) => Promise<void> | void;
  isSubmitting?: boolean;
};

const CaseForm = ({ onCreate, isSubmitting = false }: CaseFormProps) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [difficulty, setDifficulty] = useState<CaseDifficulty>("medium");

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setDifficulty("medium");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!title.trim() || !description.trim()) {
      return;
    }

    try {
      await onCreate({
        title: title.trim(),
        description: description.trim(),
        difficulty,
      });
      resetForm();
    } catch {
      // Error is handled upstream; keep current form state for correction.
    }
  };

  return (
    <form className="card form-card" onSubmit={handleSubmit}>
      <h2 className="card-title">Create Case</h2>
      <div className="form-grid">
        <label className="form-field">
          <span>Title</span>
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Missing journalist in District 4"
            required
          />
        </label>
        <label className="form-field">
          <span>Difficulty</span>
          <select
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value as CaseDifficulty)}
          >
            {difficulties.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="form-field form-field-full">
          <span>Description</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Outline the key beats, main suspects, and investigative hooks."
            rows={4}
            required
          />
        </label>
      </div>
      <button className="button" type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating..." : "Create Case"}
      </button>
    </form>
  );
};

export default CaseForm;
```

- [ ] **Step 8: Run the build**

Run: `cd frontend && npm run build`
Expected: PASS. (`tsc -b` fails the build if anything still references `userId`, `updateCase` or the removed payload fields.)

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "fix(frontend): case form only sends fields the API accepts"
```

---

### Task 7: Documentation, final verification, local merge

**Files:**
- Modify: `CLAUDE.md`, `backend/README.md`

- [ ] **Step 1: Update `CLAUDE.md`**

Re-read the file first (it was written before these changes), then:

1. In the Commands block, replace the `pytest` line with:
   `pytest                               # in-memory SQLite, no services needed; single test: pytest tests/test_cases_authz.py::test_name`
2. In **Architecture notes → Models**, append: `` `User` is the exception: it is a plain SQLAlchemy declarative model (fastapi-users cannot be mixed into a SQLModel table) that shares `SQLModel.metadata`, so foreign keys to `users.id` still work. ``
3. Add a new paragraph under **Architecture notes**:
   `**Server authority.** Players never write owner ids, rewards, progress, suspicion/trust or game-state values. The owner always comes from the JWT; cases are reached through the `get_owned_case` dependency (`app/api/deps.py`); a missing or foreign resource is a 404. Characters are superuser-authored and `CharacterRead` omits `is_guilty`. There are deliberately no PATCH routes for cases, characters or game state — outcome changes belong to the rules engine (see `docs/superpowers/plans/2026-10-12-improvement-roadmap.md`).`
4. Replace the whole **Gotchas / known gaps** list with:
   - `No Alembic setup yet (planned: Plan 2). Schema comes from create_all at startup, which does not alter existing tables.`
   - `Tests run on SQLite; Postgres-specific behaviour (length limits, FK enforcement, unique races) is untested until Plan 2.`
   - `Lint baseline is not green (ruff, black, mypy); see Plan 2.`
   - `The GDD (DGD/) describes a different game (terminal narrative, SvelteKit, Message/Order/Event model) than the detective-case code; decision D1 in the roadmap is open.`
   - Keep the Python 3.9 syntax bullet and the game-tuning-constants bullet unchanged.

- [ ] **Step 2: Update `backend/README.md`**

- Remove the `PATCH /api/v1/cases/{case_id}`, `PATCH /api/v1/characters/{character_id}` and `PATCH /api/v1/game-state/me` lines.
- Change `POST /api/v1/characters/` to `POST /api/v1/characters/ - Create new character (superuser only)` and `DELETE /api/v1/characters/{character_id}` to `… - Delete character (superuser only)`.
- Change `POST /api/v1/game-state/` to `POST /api/v1/game-state/ - Start a game (no body; server defaults; 409 if one exists)`.
- Fix the stray `docscd b` typo on the "API Documentation" feature line (`Auto-generated OpenAPI/Swagger docs`).
- In **Testing**, state that tests need no database or Redis.

- [ ] **Step 3: Full verification**

```bash
cd backend && source venv/bin/activate
pytest -q -p no:warnings            # expected: 23 passed
ruff check app tests | tail -3       # expected: Found ≤ 4 errors (baseline: 4)
cd ../frontend && npm run build      # expected: ✓ built
```

Optional end-to-end smoke (needs Docker; **not executed during planning**):

```bash
cd backend && cp .env.example .env && docker-compose up --build -d
curl -s localhost:8000/health        # {"status":"healthy"}
curl -s -X POST localhost:8000/api/v1/auth/register -H 'content-type: application/json' \
  -d '{"email":"a@a.com","username":"alice","password":"correct-horse-battery"}'   # 201
docker-compose down
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md backend/README.md
git commit -m "docs: document server-authoritative rules and update API docs"
```

- [ ] **Step 5: Merge locally (no push, no PR)**

Ask the user to confirm first, then:

```bash
git checkout main
git merge --no-ff fix/boot-and-authz-hardening -m "Merge: boot and authorization hardening"
git log --oneline -n 10
```

---

## Self-Review

**Spec coverage** (roadmap §1): F1 → Task 1. F2 → Task 6 Steps 1–6. F3 → Task 4. F4 → Tasks 3, 4, 5. F5 → Task 2. F6 → Task 2. F7 (docs half: Alembic/pytest claims) → Task 7; the lint/Alembic work is explicitly Plan 2. F8 is decision D1 and is intentionally out of scope. No gaps.

**Placeholder scan:** no TBD/TODO; every code step has full code; the only non-code edits (Task 7 docs) list exact bullets/lines to change.

**Type consistency:** `make_user` signature and `user1`/`user2` naming are identical in all test files; `get_owned_case` is defined in Task 3 and consumed with the same name in Task 4; `current_superuser` defined in Task 4 Step 3 and used in Step 6; `CaseCreate` fields match `CaseCreatePayload` on the frontend; `USERNAME_MIN_LENGTH/MAX_LENGTH` defined and used only in `user.py`.

**Review Focus coverage:** all five lines map to named tests (Tasks 2, 3, 4, 5).

**Expected test counts:** 2 after Task 1, 9 after Task 2, 15 after Task 3, 20 after Task 4, 23 after Task 5.

**Validation status:** every code block was executed in a scratch copy of the repo (Python 3.9.6 venv; frontend via `npm ci`): 23 backend tests passed and `npm run build` passed, but the plan was *not* replayed task-by-task in the real repo, and nothing ran against Docker/Postgres.
