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
python -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt   # Python 3.9 (Dockerfile); requirements.txt is the runtime set
docker-compose up --build            # postgres, redis, backend (:8000, --reload), celery_worker
uvicorn app.main:app --reload        # local; DATABASE_URL may also be sqlite+aiosqlite:///./dev.db (no Docker)
pytest                               # SQLite in memory, no services; one test: pytest tests/test_shifts_api.py::test_name
TEST_DATABASE_URL=postgresql+asyncpg://… pytest   # same suite on real PostgreSQL (drops/recreates its tables!)
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

**Content is data.** A shift is `backend/content/<name>.json`, parsed into `ShiftContent` (`engine/models.py`, unknown keys and duplicate JSON keys are rejected) and checked by `engine/content.validate_content` (duplicate ids, missing or shadowing catch-all ending, flags used but never set, messages or endings whose flags cannot be produced, unresolvable messages). `tests/engine/test_content.py` also plays thousands of seeded random shifts and fails if an ending becomes unreachable or an invariant breaks, plus scripted playthroughs for specific endings — run it after editing content. The clock only advances through commands (`read` 2 min, `execute` 5, `deny` 3, `delay` 1, `investigate` 10, `wait n` 1–60); fatigue accrues 5 per hour. `delay` and `investigate` are non-resolving: once per message, the message stays open. A message expires at `expires_at`, but never sooner than 30 minutes after it was actually delivered (`rules.deadline`), so a gated message cannot arrive already expired; `inbox` and the API show the deadline. `clockout` is refused before `earliest_clockout_minutes` (02:00 in night_one).

**Persistence.** `Shift.state` is a serialized `ShiftState` (JSON column). A partial unique index allows one unfinished shift per user. Tables are created by `init_db()` (`SQLModel.metadata.create_all`) at startup, serialised across workers with a PostgreSQL advisory lock (without it 3 of 4 simultaneous workers crash). Deleting a user cascades to their shifts and logs. `User` is a plain SQLAlchemy declarative model sharing `SQLModel.metadata` (fastapi-users cannot be mixed into a SQLModel table), so `ForeignKey("users.id")` still works.

**Auth.** Routes are assembled in `routes/auth.py`. Login is `POST /auth/jwt/login`, form-encoded, and the `username` field is the **email**. Register is `/auth/register` (username 3–50 chars, password ≥ 8, duplicate username → 400). The frontend keeps the token in `localStorage` (`AuthContext`) and revalidates it through `/auth/users/me`; all HTTP goes through `request()` in `src/api/client.ts`.

**Frontend flow.** `useShift` (hooks) owns the shift view and scrollback: on load it fetches the current shift and replays `/shifts/current/log`; `send` posts a command and appends the echoed command plus returned events. `TerminalPage` composes `Hud`, `Inbox` (buttons send the same commands as typing) and `CommandInput` (history with arrows, Tab completion in `terminal/completion.ts`). Tests mock `src/api/shifts`.

## Gotchas / known gaps

- **No Alembic yet.** The schema comes from `create_all`, which does not alter existing tables: after changing a model, reset the dev database.
- **Config is safe by default.** `DEBUG` defaults to false; with it off the app refuses placeholder/short (<32) secrets. `DEBUG=true` (local only) also logs reset tokens. SQL logging is a separate `SQL_ECHO`.
- **Content edits vs. running shifts.** A shift stores only `content_name`. Views and `inbox` tolerate a removed message id, but renaming ids or changing flags still skews shifts in progress: treat published content as append-only, or add a new `<name>` file.
- **No rate limiting and no log retention.** Every accepted or rejected command writes an `action_logs` row until the shift ends (a finished shift writes nothing), and a player can start shifts in a loop. An abandoned shift stays active until it is played out.
- Tests default to SQLite; PostgreSQL-only behaviour is covered by running the suite with `TEST_DATABASE_URL`. CI (`.github/workflows/ci.yml`) runs `ruff check app tests` and `pytest` on Python 3.9, and `npm run build` + `npm test` for the frontend; those gate merges. `black --check`, `isort --check` and `mypy app` still report issues on older code, so CI runs them as advisory only (config in `backend/pyproject.toml`).
- Redis and Celery are configured but unused by the game. The GDD's SSE stream, observability and LLM layer are not built; the GDD names SvelteKit and the client is React (decision deferred, see the roadmap).
- Python 3.9 syntax only (`Optional[X]`, not `X | None`), matching the Dockerfile.

## Working rules

Apply these on every change, in addition to the architecture above. User instruction in the conversation overrides this file.

1. **Verify, don't invent.** Read the source of truth before using an endpoint, field, command name, content flag or signature: `engine/models.py` for schemas, `backend/content/*.json` for content, `src/api/*.ts` and `routes/*.py` for the API contract, the GDD in `DGD/` for design intent. If something could not be verified, say exactly what.
2. **Stay in scope.** Change only what the task needs, plus required collateral (call sites, types, fixtures, tests for the changed behavior). No refactors for taste, renames of working code, drive-by fixes, dependency bumps or whole-file reformatting. Note anything found on the side in the PR description instead of fixing it.
3. **Decide, then declare.** Cheap-to-reverse choices (names, layout, implementation details): decide and record the assumption. Ask first when the requirement is ambiguous in a way that changes the solution, or the decision is expensive to reverse: DB schema, public API contract, published content ids/flags, a new dependency, infra. Put all blocking questions in one message, with a recommendation each.
4. **Simplest thing that fits.** Follow existing patterns. No abstraction, flag or config layer for a hypothetical future case.
5. **Behavior change needs a test**, in the same PR, in the existing style: rules in `tests/engine/`, API in `tests/test_*_api.py`, UI next to the component as `*.test.tsx`. If a test is impractical, say why and how it was verified by hand. After editing `backend/content/`, run `pytest tests/engine/test_content.py`.
6. **Errors and logs.** Never swallow an exception (no bare `except: pass`, no empty `catch {}`; ruff `BLE` is enforced). Log with enough context to diagnose (operation, shift/user id, failing field) and never log raw payloads, command text from players, passwords, tokens or auth headers: log field names and the error, not the values. No `print()` in `app/` (ruff `T20`).
7. **Never commit secrets.** `.env` stays untracked; only `.env.example` with placeholders. Do not weaken the config guard that rejects placeholder or short secrets when `DEBUG` is off.
8. **Verify before saying it is done.** Run the commands in "Commands": `ruff check app tests` and `pytest` in `backend/`, `npm run build` and `npm test` in `frontend/`. Report what failed rather than "should work".
9. **Uncertainty comes with options.** If unsure, state the doubt and the options considered with the trade-off of each; no generic "please review carefully".
10. **Git.** One branch per feature or fix, one logical change per PR, nothing straight to `main` (it is protected: PR + passing `backend` and `frontend` checks). Use the PR template.

When finishing a code change, end with: **Changed**, **Tested** (commands and results), **Assumptions**, **Findings** (out of scope). Omit empty sections.
