# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Nightshift Analyst is a detective-themed narrative game. The monorepo has two independent apps and a design doc:

- `backend/` — FastAPI + SQLModel + PostgreSQL (asyncpg) + Redis + Celery. Auth via `fastapi-users` (JWT bearer).
- `frontend/` — Vite + React 18 + TypeScript client (login and case dashboard only so far). No UI/test libraries beyond `react-router-dom`.
- `DGD/` — the Game Design Document PDF; the authority on narrative, characters and mechanics. Check it before gameplay/content changes.

## Commands

Backend (run from `backend/`; copy `.env.example` to `.env` first — `SECRET_KEY` and `JWT_SECRET_KEY` have no defaults, so the app won't import without them):

```bash
docker-compose up --build            # postgres, redis, backend (:8000, --reload), celery_worker
uvicorn app.main:app --reload        # local, non-Docker (needs Postgres + Redis running)
celery -A app.tasks.celery_app worker --loglevel=info
black app/ && isort app/ && ruff check app/ && mypy app/
pytest                               # single test: pytest path/to/test_file.py::test_name
```

Frontend (run from `frontend/`):

```bash
npm install
npm run dev        # :5173
npm run build      # tsc -b && vite build — this is the only type-check/lint step
```

Swagger UI is at http://localhost:8000/docs. The frontend reads `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).

## Architecture notes

**Backend request flow.** `app/main.py` mounts `app.api.v1.api_router` under `settings.API_V1_PREFIX` (`/api/v1`). Route modules in `app/api/v1/routes/` (`auth`, `cases`, `characters`, `game_state`) are registered in `app/api/v1/__init__.py` — add new routers there. Routes get an `AsyncSession` from `app.database.get_session` and the authenticated user from `app.auth.users.current_active_user`.

**Models** (`app/models/`): each file defines a SQLModel table plus `*Create/*Read/*Update` schemas, all re-exported from `app/models/__init__.py`. Tables are created by `init_db()` (`SQLModel.metadata.create_all`) in the FastAPI lifespan, so a new model must be imported in `app/models/__init__.py` to be picked up.

**Settings** (`app/config.py`): a single pydantic-settings `settings` object read from `.env`. `database.py` rewrites `postgresql://` to `postgresql+asyncpg://` itself, so keep `DATABASE_URL` in the plain `postgresql://` form. In Docker Compose, the `environment:` block overrides `.env` for DB/Redis/Celery hosts.

**Auth.** `fastapi-users` routes are assembled in `routes/auth.py`: login is `POST /auth/jwt/login` (form-encoded `username`/`password`, where `username` is the email), register is `/auth/register`, profile is `/auth/users/me`. The frontend `src/api/auth.ts` matches these. The frontend stores the token and user in `localStorage` (`AuthContext`) and re-validates through `/auth/users/me` on load; all HTTP goes through `request()` in `src/api/client.ts`, which throws `ApiError` using the backend's `detail`.

**Celery** (`app/tasks/celery_app.py`) shares the Redis instance with the cache. It only has a `health_check` task so far; `autodiscover_tasks(["app"])` looks for a `tasks` module inside `app`.

## Gotchas / known gaps (verify before relying on the READMEs)

- **No Alembic setup and no tests exist.** The READMEs reference `alembic upgrade head` and `pytest`, but there is no `alembic.ini`, no `migrations/` directory, and no `tests/` directory. The schema comes from `create_all`, which won't alter existing tables, so model changes against an existing DB need a manual reset or a real Alembic setup.
- **Ownership checks are inconsistent.** `cases.py` filters reads/updates/deletes by `Case.user_id == user.id`, but `create_case` takes `user_id` from the request body (`CaseCreate.user_id`) instead of the authenticated user. Check the equivalent in `characters.py` and `game_state.py` when touching them.
- `auth/backend.py` has `BearerTransport(tokenUrl="auth/login")`, which doesn't match the real `/auth/jwt/login` path (it only affects the Swagger "Authorize" button).
- The Docker image is Python 3.9, but `backend/README.md` mentions 3.9+. Keep syntax 3.9-compatible (`Optional[X]`, not `X | None`) to match the existing code.
- Game-tuning constants (`MAX_CASES_PER_DAY`, `STRESS_INCREMENT_RATE`, …) live in `Settings`, not in the models.
