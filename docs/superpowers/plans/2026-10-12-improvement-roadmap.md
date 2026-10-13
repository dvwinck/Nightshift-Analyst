# Nightshift Analyst — Improvement Roadmap

> Umbrella document. Each numbered plan below is a separate, independently shippable plan.
> **Plan 1 is fully detailed** in `2026-10-12-boot-and-authz-hardening.md`. Plans 2–6 are outlines
> that must be expanded (with `superpowers:writing-plans`) only after their dependencies land,
> and Plans 3–5 only after decision **D1**.

## 1. What the analysis found (all verified by running code, not only reading it)

| # | Finding | Evidence |
|---|---|---|
| F1 | **The backend does not start.** `User(UserBase, SQLAlchemyBaseUserTableUUID, table=True)` mixes SQLModel with fastapi-users' SQLAlchemy 2.0 `Mapped[...]` table. | `import app.models.user` → `PydanticSchemaGenerationError: Unable to generate pydantic-core schema for sqlalchemy.orm.base.Mapped[str]`. Reproduced with pydantic 2.13.5 **and** 2.10.6 (not version drift). |
| F2 | `npm run build` fails on a clean checkout. | `tsconfig.node.json` is `composite` + `noEmit` (TS6310), has no `lib`/`target` (108 TS errors from `Set`/`Symbol`), plus a real narrowing error at `src/api/client.ts:44`. |
| F3 | No object-level authorization on characters; `CharacterRead` exposes `is_guilty`. | Any logged-in user can read/edit/delete any character and read the solution. |
| F4 | The client chooses ownership and outcomes. | `user_id`/`case_id` come from the request body; `PATCH /game-state/me` and `PATCH /cases/{id}` accept `reputation`, `cases_solved`, `status`, `clues_found`. |
| F5 | Registering an existing username raises an unhandled `IntegrityError` (500). Over-long usernames pass on SQLite but break on Postgres (`String(50)`). | Probe tests. |
| F6 | Reset/verification tokens are `print()`ed to stdout. Swagger `tokenUrl` points to a non-existent route. | `app/auth/manager.py`, `app/auth/backend.py`. |
| F7 | README/GDD mention Alembic and `pytest`; neither exists. Lint baseline is not green (ruff 4 errors, black 6 files, mypy 14 errors). | `ruff check`, `black --check`, `mypy` on the original code. |
| F8 | **The code and the GDD describe different games.** | See D1. |

## 2. Decision D1 — which game are we building? (blocks Plans 3–5, not Plans 1–2)

| | GDD (`DGD/…pdf`) | Current code |
|---|---|---|
| Premise | Night-shift analyst, classified agency, a conspiracy; terminal UI | Detective investigating cases, suspects, witnesses |
| Entities | Player, Message, Order, Event, Session, ActionLog | Case, Character, Decision, GameState |
| Metrics | Technical / Ethical / Political | Stress / Reputation |
| Loop | Receive → Interpret → Act → React → Reflect | CRUD over cases |
| Frontend | SvelteKit + Tailwind/DaisyUI | React 18 + Vite |
| Realtime | SSE/WebSocket (`/api/stream`, `/api/commands`) | REST only |

**Recommendation (owner's call):** treat the GDD as the source of truth for *concept and mechanics*
(the README already calls it "authoritative"), keep FastAPI/Postgres/Redis/Celery as-is, and defer
React-vs-Svelte to Plan 5 — the frontend is ~15 small files, so the switch is cheap *now* and costly later.
The detective `Case/Character/Decision` models then become either (a) reused as the content model for
"investigation" events, or (b) retired. **Plan 1 is deliberately safe under either answer.**

## 3. Sequence

| Plan | Goal | Depends on | Exit criteria |
|---|---|---|---|
| **1. Boot & authorization hardening** (detailed) | App boots; tests exist; no cross-user access; client cannot write outcomes; frontend builds | — | `pytest` green (23 tests), `npm run build` green |
| **2. Foundations** | Alembic baseline; tests also run on real Postgres; CI (GitHub Actions); pre-commit; make ruff/black/mypy green; pin `pydantic`; `docker-compose` smoke | 1 | CI green on PR; `alembic upgrade head` on empty DB; `alembic revision --autogenerate` yields no diff |
| **3. Rules engine & commands** | Pure `apply_command(state, command) -> (state, events)`; `POST /commands`; `ActionLog`; metrics with bounds | 1, **D1** | Engine unit tests need no DB; every state change goes through a command; illegal commands rejected + logged |
| **4. Narrative content & realtime** | Storylet/QBN content as validated JSON; condition/effect evaluation; SSE feed | 3 | A scripted playthrough test reaches ≥2 distinct endings; SSE delivers events in order |
| **5. Frontend** | Terminal UI on the new API; TanStack Query; ESLint + Vitest + Playwright happy path | 3 (4 for the feed), D1 | Playwright: login → read message → issue command → see consequence |
| **6. Operations (optional)** | Sentry/OpenTelemetry, `fastapi-limiter`, optional LiteLLM adversary messages (Pydantic-validated) | 2 | Rate limit returns 429; traces visible locally |

## 4. Design principles to hold every plan to

1. **Server authoritative.** Clients send *intent* ("execute order-773"), never *results* ("reputation = 100").
   References: [AccelByte — server-authoritative logic](https://accelbyte.io/blog/server-authoritative-logic-to-prevent-cheating),
   [Bugnet — validate player actions server-side](https://bugnet.io/blog/how-to-validate-player-actions-server-side).
2. **Object- and property-level authorization on every route** (OWASP API Security Top 10, 2023: API1 BOLA, API3 BOPLA).
   References: [ISACA review of the 2023 list](https://www.isaca.org/resources/news-and-trends/industry-news/2023/reviewing-the-2023-owasp-api-top-10),
   [Barracuda — BOPLA](https://blog.barracuda.com/2023/05/23/owasp-top-10-api-broken-object-property-level-authorization).
3. **Rules as pure functions, I/O at the edge** (Command, State, Event Queue — *Game Programming Patterns*):
   [contents](https://gameprogrammingpatterns.com/contents.html).
4. **Content as data** — quality-based narrative / storylets: metrics are *qualities* that gate content.
   References: [Failbetter, "Adventures in Text" (GDC Vault)](https://gdcvault.com/play/1021775/Adventures-in-Text-Innovating-in),
   [TinyQBN terms and concepts](https://videlais.com/tag/qbn/page/2/).
5. **Design to the target feeling (MDA).** The GDD's target aesthetic is *the weight of a decision*; mechanics must give
   choices cost, incomplete information and delayed consequence, not only ±numbers.
   Reference: [Hunicke, LeBlanc, Zubek — MDA](https://users.cs.northwestern.edu/~hunicke/MDA.pdf).

## 5. Known limits of this analysis

- Tests in Plan 1 run on in-memory SQLite. Postgres-specific behaviour (length limits, FK enforcement,
  `UNIQUE` races) is only covered once Plan 2 adds a Postgres test job.
- Nothing was run against Docker/Postgres/Redis/Celery; the Celery worker and `docker-compose` were read, not executed.
- Plan 1's code was validated in a scratch copy (Python 3.9.6 venv, requirements installed unpinned for transitive
  packages, pydantic 2.13.5), not in the repository.
