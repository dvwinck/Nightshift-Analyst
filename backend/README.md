# Nightshift Analyst - Backend API

FastAPI backend for Nightshift: Analyst, a narrative terminal game. The game rules are a pure engine (`app/engine/`); the API only loads a shift, runs one command and stores the result.

## Features

- **Authentication**: JWT-based authentication with FastAPI Users
- **Database**: PostgreSQL with SQLModel/SQLAlchemy ORM
- **Async Support**: Fully asynchronous API using asyncio and asyncpg
- **Redis / Celery**: configured for future use (live events, background jobs); the game does not use them yet
- **Background Tasks**: Celery for async task processing
- **API Documentation**: Auto-generated OpenAPI/Swagger docs
- **Type Safety**: Full type hints with Pydantic models
- **Docker Support**: Containerized deployment with Docker Compose

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Application configuration
│   ├── database.py          # Database connection and session management
│   ├── engine/              # PURE game rules (no DB, no HTTP)
│   │   ├── models.py        #   content / state / event schemas
│   │   ├── rules.py         #   apply_command(state, raw, content)
│   │   ├── content.py       #   load + validate shift content
│   │   └── view.py          #   what the client is allowed to see
│   ├── services/shifts.py   # load/save state, compare-and-set, action log
│   ├── models/              # User (fastapi-users) and Shift / ActionLog tables
│   ├── auth/                # JWT backend, user manager, FastAPI Users instance
│   └── api/v1/routes/       # auth.py, shifts.py
├── content/night_one.json   # the first shift, as data
├── tests/                   # pytest (SQLite in memory); tests/engine for the rules
├── requirements.txt, Dockerfile, docker-compose.yml, .env.example
└── pytest.ini
```

## Setup

### Prerequisites

- Python 3.9+ (the Dockerfile uses 3.9)
- PostgreSQL 15+ for real use. For a quick local run you can instead set `DATABASE_URL=sqlite+aiosqlite:///./dev.db`
- Docker & Docker Compose (optional; starts PostgreSQL, Redis, the API and a Celery worker)

Redis is not required to play: nothing in the game reads it yet.

### Local Development

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt     # requirements.txt is the runtime set only
cp .env.example .env                    # DEBUG=true and placeholder secrets: local use only
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Tables are created on startup
(`create_all`); there are no Alembic migrations yet, so after changing a model reset your dev database.

### Docker Development

```bash
cp .env.example .env
docker-compose up --build
```

Ports are bound to `127.0.0.1` only. The compose file runs the API with `--reload`; the image's own
command does not. The API will be available at `http://localhost:8000`.

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/jwt/login` - Login (get JWT token)
- `POST /api/v1/auth/jwt/logout` - Logout
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password
- `GET /api/v1/auth/users/me` - Get current user
- `PATCH /api/v1/auth/users/me` - Update current user

### Shifts

All shift routes require a bearer token. The client only ever sends a command; every
outcome is computed on the server.

- `POST /api/v1/shifts/` - Start a shift (409 while one is in progress)
- `GET /api/v1/shifts/current` - Latest shift: clock, metrics and inbox (unread bodies are never sent)
- `POST /api/v1/shifts/current/commands` - Body `{"command": "read order-773"}` (1-200 characters, no control characters, else 422). A rejected command answers 200 with `accepted: false`; 404 if no shift was started; 409 if another request changed the shift first (retry); a finished shift answers `accepted: false` and writes nothing
- `GET /api/v1/shifts/current/log?limit=100` - Replay of the last commands, oldest first

Commands: `help`, `status`, `inbox` (shows when each message expires), `read <id>` (2 min), `execute|deny <id>`
(5 / 3 min), `delay <id>` (1 min) and `investigate <id>` (10 min; both once per message, the message stays open),
`wait [minutes]` (default 15, max 60), `clockout` (refused before 02:00). Fatigue rises 5 per hour of shift time.
A message is never taken away sooner than 30 minutes after it was delivered.

## Environment Variables

See `.env.example` for the complete list. The important ones:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/nightshift_analyst   # or sqlite+aiosqlite:///./dev.db
SECRET_KEY=...        # 32+ characters
JWT_SECRET_KEY=...    # 32+ characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=false           # true only for local development
SQL_ECHO=false        # log every SQL statement (with parameters)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

With `DEBUG=false` (the default) the app **refuses to start** if a secret is a placeholder
(`your-...`, `...change-in-production`) or shorter than 32 characters. With `DEBUG=true` verbose errors
are on and password-reset/verification tokens are written to the log (there is no email delivery yet);
never enable it in production.

## Database Models

- **User** - fastapi-users account (email, username, password hash, flags)
- **Shift** - one play-through: serialized `ShiftState`, `version` for optimistic concurrency, start/end times. A partial unique index allows one unfinished shift per user
- **ActionLog** - every command a player sent (accepted or not) with the events it produced

## Testing

Run tests with pytest (by default no services are needed: it uses in-memory SQLite):

```bash
pytest
pytest tests/engine   # rules engine only
```

Run the same suite against a real PostgreSQL (also enables the concurrent schema-creation test):

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/nightshift_test pytest
```

The tests drop and recreate every table in that database, so point it at a scratch database.

## Code Quality

Format code with Black:

```bash
black app/
```

Sort imports with isort:

```bash
isort app/
```

Lint with Ruff:

```bash
ruff check app/
```

Type check with mypy:

```bash
mypy app/
```

## Production Deployment

1. Set `DEBUG=false` and real 32+ character `SECRET_KEY` / `JWT_SECRET_KEY` (startup fails otherwise)
2. Run several workers: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`
   (schema creation is serialised with a PostgreSQL advisory lock, so workers can start together)
3. Terminate TLS in front of the app and set `ALLOWED_ORIGINS` to your real frontend origin
4. Do not publish PostgreSQL or Redis to the internet (the compose file binds them to localhost)
5. Known gaps before real traffic: no rate limiting, no retention policy for `action_logs`,
   no Alembic migrations (see `docs/superpowers/plans/2026-10-12-improvement-roadmap.md`)

## License

See the main project LICENSE file.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.
