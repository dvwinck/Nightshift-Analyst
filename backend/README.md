# Nightshift Analyst - Backend API

FastAPI backend for the Nightshift Analyst detective game.

## Features

- **Authentication**: JWT-based authentication with FastAPI Users
- **Database**: PostgreSQL with SQLModel/SQLAlchemy ORM
- **Async Support**: Fully asynchronous API using asyncio and asyncpg
- **Caching**: Redis for session management and caching
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

- Python 3.9+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone the repository and navigate to backend directory:**

```bash
cd backend
```

2. **Create a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Start PostgreSQL and Redis** (if not using Docker)

6. **Run database migrations:**

```bash
alembic upgrade head
```

7. **Start the development server:**

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Docker Development

1. **Build and start all services:**

```bash
docker-compose up --build
```

2. **Run migrations inside the container:**

```bash
docker-compose exec backend alembic upgrade head
```

The API will be available at `http://localhost:8000`

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
- `POST /api/v1/shifts/current/commands` - Body `{"command": "read order-773"}`. A rejected command answers 200 with `accepted: false`
- `GET /api/v1/shifts/current/log?limit=100` - Replay of the last commands, oldest first

Commands: `help`, `status`, `inbox`, `read <id>`, `execute|deny <id>`, `delay <id>` and `investigate <id>`
(once per message, the message stays open), `wait [minutes]`, `clockout`.

## Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nightshift_analyst

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Application
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Database Models

- **User** - fastapi-users account (email, username, password hash, flags)
- **Shift** - one play-through: serialized `ShiftState`, `version` for optimistic concurrency, start/end times. A partial unique index allows one unfinished shift per user
- **ActionLog** - every command a player sent (accepted or not) with the events it produced

## Testing

Run tests with pytest (no database or Redis needed; it uses in-memory SQLite):

```bash
pytest
pytest tests/engine   # rules engine only
```

Run tests with coverage:

```bash
pytest --cov=app
```

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

1. Set `DEBUG=False` in environment variables
2. Use a production-grade ASGI server (e.g., gunicorn with uvicorn workers)
3. Set up proper SSL/TLS certificates
4. Configure database connection pooling
5. Set up monitoring and logging
6. Use environment-specific secrets

Example production command:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## License

See the main project LICENSE file.

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.
