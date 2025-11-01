# Nightshift Analyst - Backend API

FastAPI backend for the Nightshift Analyst detective game.

## Features

- **Authentication**: JWT-based authentication with FastAPI Users
- **Database**: PostgreSQL with SQLModel/SQLAlchemy ORM
- **Async Support**: Fully asynchronous API using asyncio and asyncpg
- **Caching**: Redis for session management and caching
- **Background Tasks**: Celery for async task processing
- **API Documentation**: Auto-generated OpenAPI/Swagger docscd b
- **Type Safety**: Full type hints with Pydantic models
- **Docker Support**: Containerized deployment with Docker Compose

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Application configuration
│   ├── database.py          # Database connection and session management
│   ├── models/              # SQLModel database models
│   │   ├── user.py
│   │   ├── case.py
│   │   ├── character.py
│   │   ├── game_state.py
│   │   └── decision.py
│   ├── auth/                # Authentication module
│   │   ├── backend.py       # JWT authentication backend
│   │   ├── manager.py       # User manager
│   │   ├── database.py      # User database operations
│   │   └── users.py         # FastAPI Users instance
│   └── api/                 # API routes
│       └── v1/
│           ├── __init__.py
│           └── routes/
│               ├── auth.py
│               ├── cases.py
│               ├── characters.py
│               └── game_state.py
├── .env.example             # Environment variables template
├── .gitignore
├── requirements.txt         # Python dependencies
├── Dockerfile
├── docker-compose.yml
└── README.md
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

### Cases

- `POST /api/v1/cases/` - Create new case
- `GET /api/v1/cases/` - List all cases for current user
- `GET /api/v1/cases/{case_id}` - Get specific case
- `PATCH /api/v1/cases/{case_id}` - Update case
- `DELETE /api/v1/cases/{case_id}` - Delete case

### Characters

- `POST /api/v1/characters/` - Create new character
- `GET /api/v1/characters/case/{case_id}` - List characters for a case
- `GET /api/v1/characters/{character_id}` - Get specific character
- `PATCH /api/v1/characters/{character_id}` - Update character
- `DELETE /api/v1/characters/{character_id}` - Delete character

### Game State

- `POST /api/v1/game-state/` - Create game state
- `GET /api/v1/game-state/me` - Get current user's game state
- `PATCH /api/v1/game-state/me` - Update game state
- `DELETE /api/v1/game-state/me` - Delete game state

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

### User
- Authentication and user profile
- Linked to game state

### Case
- Investigation cases with difficulty levels
- Tracks completion status and time limits
- Contains evidence and clues

### Character
- NPCs in cases (suspects, witnesses, victims)
- Personality traits and dialogue history
- Suspicion and trust levels

### GameState
- Player progression and statistics
- Current day, stress, reputation
- Unlocked features and achievements

### Decision
- Player choices during investigations
- Links to cases and characters
- Tracks outcomes and impacts

## Testing

Run tests with pytest:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=app tests/
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
