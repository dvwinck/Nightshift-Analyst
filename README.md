# Nightshift Analyst

Detective-themed narrative game that blends investigation mechanics with narrative branching. The repository currently focuses on the backend API that powers the experience and includes the core game design document for reference.

## Project Structure

- `backend/` – FastAPI backend service with PostgreSQL, Redis, and Celery integrations (see `backend/README.md` for full docs)
- `frontend/` – Vite + React client for authentication and case management dashboards
- `DGD/` – Game design document (`Game Design Document — Nightshift_ Analyst.pdf`)
- `LICENSE` – MIT license for the project

## Quick Start

1. **Set up the backend**
   ```bash
   cd backend
   cp .env.example .env
   docker-compose up --build
   ```
   This boots PostgreSQL, Redis, the FastAPI app, and worker services defined in `docker-compose.yml`. Update the `.env` file with secrets before running in production.

2. **Run migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

3. **Explore the API**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

Refer to `backend/README.md` for local (non-Docker) setup, testing, linting, and deployment tips.

4. **Run the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   By default the client points to `http://localhost:8000/api/v1`. Override with `VITE_API_BASE_URL` in a `.env` file if your backend runs elsewhere.

## Game Design Document

The `DGD/` directory contains the authoritative game design document. Review it to understand narrative arcs, characters, core mechanics, and planned content before making gameplay or content changes.

## Contributing

1. Create a new branch per feature or fix.
2. Follow backend coding standards (`black`, `ruff`, `mypy`) before committing.
3. Ensure tests pass (`pytest`) and update documentation when behavior changes.

## License

Nightshift Analyst is released under the MIT License. See `LICENSE` for details.
