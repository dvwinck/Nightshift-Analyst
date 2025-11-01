# Nightshift Analyst – Frontend

First pass of the Nightshift Analyst client application. Built with Vite, React, and TypeScript to cover authentication and core case-management flows against the FastAPI backend.

## Prerequisites

- Node.js 18+
- npm 9+ (or another Node package manager)

## Getting Started

```bash
cd frontend
npm install
npm run dev
```

The development server runs on http://localhost:5173 by default. The client expects the backend at `http://localhost:8000/api/v1`; configure a different base URL by creating `.env` in this directory:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Run with Docker Compose

```bash
cd frontend
docker compose up --build
```

The service mounts your working directory for hot reloading. Override the API endpoint by exporting `VITE_API_BASE_URL` before starting, e.g. `VITE_API_BASE_URL=https://api.example.com docker compose up`.

## Available Scripts

- `npm run dev` – start the Vite dev server with hot module replacement
- `npm run build` – type-check and generate a production build
- `npm run preview` – serve the production build locally

## Project Layout

- `src/api/` – lightweight fetch wrappers for authentication and case CRUD
- `src/components/` – reusable UI elements (layout shell, case cards, forms)
- `src/context/` – React context for session management
- `src/pages/` – route-level screens (login, dashboard)
- `src/styles/` – global styling primitives

## Current Functionality

- JWT login (FastAPI Users) with session persistence
- Fetch, display, and create investigation cases for the authenticated analyst
- Basic dark-theme styling tuned for the detective dashboard aesthetic

## Next Steps

- Wire registration and password resets to the corresponding auth endpoints
- Add case detail views and editing, including evidence breakdowns
- Integrate character and game-state endpoints once exposed in the backend
- Layer in automated tests (React Testing Library, Playwright) as flows mature
