# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Nightshift: Analyst is a narrative terminal game: a night-shift analyst reads messages, decides, and lives with the consequences (see `DGD/` for the Game Design Document, the authority on tone, themes and mechanics). The monorepo has:

- `backend/` — FastAPI + SQLModel + PostgreSQL (asyncpg). Auth via `fastapi-users` (JWT bearer). The game rules live in a pure engine.
- `frontend/` — Vite + React 18 + TypeScript terminal client, tested with Vitest + Testing Library.
- `docs/superpowers/plans/` — the improvement roadmap and plans (what is done, what is next, and open decision D1).

## Commands

Backend (run from `backend/`; `cp .env.example .env` first — `SECRET_KEY` and `JWT_SECRET_KEY` have no defaults, so the app will not import without them):

```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt   # Python 3.9 (Dockerfile)
docker-compose up --build            # postgres, redis, backend (:8000, --reload), celery_worker
uvicorn app.main:app --reload        # local; DATABASE_URL may also be sqlite+aiosqlite:///./dev.db (no Docker)
pytest                               # SQLite in memory, no services; one test: pytest tests/test_shifts_api.py::test_name
pytest tests/engine                  # the rules engine only (fast, no DB)
```

Frontend (run from `frontend/`):

```bash
npm install
npm run dev        # :5173; expects the API at VITE_API_BASE_URL (default http://localhost:8000/api/v1)
npm test           # vitest run
npm run build      # tsc -b && vite build — also the only type-check
```

## Architecture

**Pure engine, thin API.** All game rules are in `app/engine/` and are pure functions: `apply_command(state, raw_command, content) -> (new_state, events, accepted)` never mutates its input and does no I/O. `app/services/shifts.py` is the only code that loads/saves a shift: it calls the engine, writes the new state with a compare-and-set on `Shift.version` (a lost race is `StaleShift` → HTTP 409), and appends every command, accepted or not, to `action_logs`. `app/api/v1/routes/shifts.py` only validates input and shapes responses. Add rules in the engine (with a unit test in `tests/engine/`), not in routes.

**Server authority.** The client sends a command string and nothing else; it can never send state, ownership or outcomes. Responses go through `engine/view.py`, which never exposes unread message bodies, effects, requirements or flags. A shift is always found through the authenticated user (`get_current_shift`), so there is no object id to forge. Keep it that way for any new route.

**Content is data.** A shift is `backend/content/<name>.json`, parsed into `ShiftContent` (`engine/models.py`, unknown keys are rejected) and checked by `engine/content.validate_content` (duplicate ids, missing catch-all ending, flags required but never set, late arrivals). `tests/engine/test_content.py` also plays thousands of seeded random shifts and fails if an ending becomes unreachable or an invariant (metrics 0–100, clock monotonic) breaks — run it after editing content. The clock only advances through commands (`read` 2 min, `execute` 5, `deny` 3, `delay` 1, `investigate` 10, `wait n`), and fatigue accrues 5 per hour. `delay` and `investigate` are non-resolving: once per message, the message stays open.

**Persistence.** `Shift.state` is a serialized `ShiftState` (JSON column). A partial unique index allows one unfinished shift per user. Tables are created by `init_db()` (`SQLModel.metadata.create_all`) at startup. `User` is a plain SQLAlchemy declarative model sharing `SQLModel.metadata` (fastapi-users cannot be mixed into a SQLModel table), so `ForeignKey("users.id")` still works.

**Auth.** Routes are assembled in `routes/auth.py`. Login is `POST /auth/jwt/login`, form-encoded, and the `username` field is the **email**. Register is `/auth/register` (username 3–50 chars, password ≥ 8, duplicate username → 400). The frontend keeps the token in `localStorage` (`AuthContext`) and revalidates it through `/auth/users/me`; all HTTP goes through `request()` in `src/api/client.ts`.

**Frontend flow.** `useShift` (hooks) owns the shift view and scrollback: on load it fetches the current shift and replays `/shifts/current/log`; `send` posts a command and appends the echoed command plus returned events. `TerminalPage` composes `Hud`, `Inbox` (buttons send the same commands as typing) and `CommandInput` (history with arrows, Tab completion in `terminal/completion.ts`). Tests mock `src/api/shifts`.

## Gotchas / known gaps

- **No Alembic yet.** The schema comes from `create_all`, which does not alter existing tables: after changing a model, reset the dev database.
- **Content edits vs. running shifts.** A shift stores only `content_name`. Removing or renaming a message id in a content file breaks shifts that are in progress. Treat published content as append-only, or create a new `<name>` file.
- Tests run on SQLite. Postgres-only behaviour (length limits, FK enforcement, unique races) is untested.
- Lint baseline is not green (`ruff`, `black --check`, `mypy` all report issues on existing code); there is no CI yet.
- Redis and Celery are configured but unused by the game; `celery_app.py` only has a `health_check` task. The GDD's SSE stream, rate limiting, observability and LLM layer are not built.
- The GDD names SvelteKit; the client is React (decision deferred, see the roadmap).
- Python 3.9 syntax only (`Optional[X]`, not `X | None`), matching the Dockerfile.
