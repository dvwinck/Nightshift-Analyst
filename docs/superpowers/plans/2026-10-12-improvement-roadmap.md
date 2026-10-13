# Nightshift Analyst — Improvement Roadmap

> Umbrella document and **status board**. Updated after the first implementation round and an independent
> review by five reviewers (security, engine correctness, game design, frontend/a11y, architecture/ops).

## 1. Decision D1 — RESOLVED: the GDD wins

The code used to implement a detective-case game while the GDD describes a night-shift analyst terminal game
(messages, orders, three metrics, consequences). The GDD was chosen: the detective domain
(`Case`, `Character`, `Decision`, `GameState` and their routes/UI) was removed and replaced by the **shift**
model (engine + API + terminal UI). React was kept for now; React-vs-SvelteKit is still open and cheap to revisit
while the client is small. Revisit before Plan 5 grows the UI.

## 2. What was found at the start (all verified by running code)

| # | Finding | Status |
|---|---|---|
| F1 | The backend did not start (`User` mixed SQLModel with fastapi-users' SQLAlchemy 2.0 table) | **Fixed** (declarative `User` on shared metadata) |
| F2 | `npm run build` failed on a clean checkout | **Fixed** |
| F3–F4 | No object-level authorization on characters; client chose ownership/outcomes | **Moot**: the domain was removed; the new API only takes a command string and resolves the shift through the token |
| F5 | Duplicate username → 500; over-long usernames | **Fixed** (+ safe charset, case-insensitive uniqueness, password 8–128) |
| F6 | Tokens printed to stdout; wrong Swagger `tokenUrl` | **Fixed** |
| F7 | README/GDD promised Alembic and tests that did not exist; lint baseline not green | Tests **done**, `ruff` **clean** on `app`/`tests`; Alembic, `black` and `mypy` **open** (Plan 6) |
| F8 | Code and GDD described different games | **Resolved** (D1) |

## 3. Plan status

| Plan | Goal | Status |
|---|---|---|
| 1. Boot & authorization hardening | App boots, tests exist, auth safe | **Done** for tasks 1, 2, 6 (3–5 dropped, see banner in its file) |
| 2. Rules engine & content | Pure engine, validated content, reachability tests | **Done** (`app/engine`, `content/night_one.json`) |
| 3. Persistence & API | `Shift`/`ActionLog`, command endpoint, optimistic concurrency | **Done** (`/api/v1/shifts…`, not `/commands` as first sketched) |
| 4. Terminal UI | Playable client | **Done** (React terminal, HUD, inbox, history, completion) |
| 5. Review round | Independent review, fixes | **Done**: see §4 |
| 6. Foundations | Alembic baseline, CI (GitHub Actions), pre-commit, green ruff/black/mypy | **Open** |
| 7. Live feed & operations | SSE message feed, rate limiting, log retention, Sentry/OTel | **Open** |
| 8. Content & design depth | More shifts, endings that read the whole record, hidden/uncertain information | **Open** (see §5) |
| 9. Browser end-to-end tests | Playwright: register → play → ending | **Open** |

## 4. Review round: what changed

Verified findings that were fixed (each has a regression test; most were first proven by a failing probe):

- **Engine totality:** `wait ²` raised `ValueError` (unicode digit) → 500 with a traceback. Fixed; the engine is fuzzed with 6000 hostile inputs.
- **Phantom penalty:** a gated message could arrive and expire in the same command, charging a penalty for something the player never saw (~6 % of random night-one runs). Fixed with a 30-minute grace from delivery.
- **Finished shifts kept writing** (`ended_at` rewritten, version bumped, a log row per command). Now a no-op.
- **Config unsafe by default:** `DEBUG` defaulted to true (tracebacks, tokens in logs, SQL with parameters echoed). Now false, SQL echo separate, and placeholder/short secrets are refused when `DEBUG` is off.
- **Concurrent startup crashed on PostgreSQL** (3 of 4 workers: `UniqueViolation`). Fixed with an advisory lock; found by running the suite on a real PostgreSQL.
- Input hygiene: control characters and lone surrogates in commands are a 422 (validation errors no longer echo the input); `POST /shifts` works with and without the trailing slash.
- Frontend: Tab no longer traps keyboard users; offline/5xx no longer logs you out; expired sessions say so; typed command restored on network failure; contrast, focus ring, ARIA for meters/inbox, dead CSS removed.
- Game-design contradictions fixed (declined promotion still ending as Company Analyst; promotion offered to someone who just leaked; "before the purge completes" after the purge), the `clockout` exploit closed (not before 02:00), deadlines shown in `inbox`.
- Infra: `.dockerignore` (a local `.env`/`venv` was being baked into the image), non-root container, ports bound to localhost, dev/runtime requirements split, FK `ON DELETE CASCADE`.
- Test quality: mutation testing of the engine (the critic found 17 surviving mutants; I re-ran those classes plus the new grace rule: 18 mutants, all killed) and of the frontend guards.

Reviewer findings **not** acted on, and why:

| Finding | Decision |
|---|---|
| Rate limiting / `action_logs` retention / shift-start loop | Plan 7; needs a product decision on limits |
| Account enumeration through register | Accepted fastapi-users trade-off; revisit with email verification |
| `Shift.state` is an untyped JSON blob without `schema_version`; content has no version | Documented in CLAUDE.md; address with Alembic (Plan 6) |
| Command list duplicated (engine help, `completion.ts`, README) | Cheap now; extract a shared list when a third client appears |
| Outcome delta lines turn morality into a scoreboard | Kept: the GDD itself shows `Obedience +5 \| Conscience -10`; revisit in Plan 8 |
| `datetime.utcnow` deprecated on Python 3.12 | Matches the Python 3.9 target; change with the runtime |
| Terminal output unbounded in memory | A shift is finite (~hundreds of lines) |

## 5. Design backlog from the playtest (Plan 8)

Measured on the engine (4000 random runs, strategy bots): Ethical and Political are strongly anti-correlated (a slider, not a triangle);
Technical gates only one ending; time pressure is weak (65–88 % of the shift is `wait`); 14 of 20 flags were dead before this round.
Applied now: endings read more of the record, reactive messages (`order-777`, `order-778`), a price for `investigate`
and for indecision, visible deadlines. Still open: make Technical matter beyond one ending, an uncertainty mechanic
(unreliable messages), more shifts, use the player's real name in the premise message, and decide whether the ethical/political
numbers should be hidden from the HUD to preserve moral ambiguity.

## 6. Principles every plan keeps

1. **Server authoritative:** clients send intent, never results ([AccelByte](https://accelbyte.io/blog/server-authoritative-logic-to-prevent-cheating), [Bugnet](https://bugnet.io/blog/how-to-validate-player-actions-server-side)).
2. **Object- and property-level authorization on every route** (OWASP API Top 10 2023: [ISACA](https://www.isaca.org/resources/news-and-trends/industry-news/2023/reviewing-the-2023-owasp-api-top-10)).
3. **Rules as pure functions, I/O at the edge** ([Game Programming Patterns](https://gameprogrammingpatterns.com/contents.html)).
4. **Content as data**, quality-based narrative / storylets ([Failbetter, GDC](https://gdcvault.com/play/1021775/Adventures-in-Text-Innovating-in)).
5. **Design to the target feeling** (MDA, [Hunicke et al.](https://users.cs.northwestern.edu/~hunicke/MDA.pdf)): "feel the weight of a decision".

## 7. Known limits of this verification

- The backend suite passes on in-memory SQLite and, run by hand with `TEST_DATABASE_URL`, on a real PostgreSQL (an embedded build, not the `postgres:15-alpine` image).
- Docker was never started: `docker-compose.yml` was validated with `docker compose config` only; the image was not built or run.
- Celery and Redis were never exercised. No CI exists yet. The UI was played by hand in one browser session and by Vitest; there is no Playwright test.
