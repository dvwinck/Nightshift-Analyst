# Nightshift Analyst

Nightshift: Analyst is a narrative terminal game about power, surveillance and moral choice: you are a night-shift analyst, messages arrive, every decision shifts three metrics (technical, ethical, political), and the shift ends in one of several endings. You play in a browser terminal.

## Project Structure

- `backend/` – FastAPI backend service with PostgreSQL, Redis, and Celery integrations (see `backend/README.md` for full docs)
- `frontend/` – Vite + React terminal client (login, account creation, the shift console)
- `docs/superpowers/plans/` – roadmap and implementation plans
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

2. **Explore the API** (tables are created on startup; Alembic is not set up yet)
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

Refer to `backend/README.md` for local (non-Docker) setup, testing, linting, and deployment tips.

3. **Run the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   By default the client points to `http://localhost:8000/api/v1`. Override with `VITE_API_BASE_URL` in a `.env` file if your backend runs elsewhere. Open http://localhost:5173, create an account, press **Start shift** and type `help`.

## Game Design Document

The `DGD/` directory contains the authoritative game design document. Review it to understand narrative arcs, characters, core mechanics, and planned content before making gameplay or content changes.

## Contributing

1. Create a new branch per feature or fix.
2. Ensure tests pass (`pytest` in `backend/`, `npm test` in `frontend/`) and update documentation when behavior changes.
3. The game rules live in `backend/app/engine/` as pure functions; content is data in `backend/content/`.

## License

Nightshift Analyst is released under the MIT License. See `LICENSE` for details.
