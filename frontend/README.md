# Nightshift Analyst – Frontend

The Nightshift: Analyst terminal client. Built with Vite, React, and TypeScript against the FastAPI backend: you read messages, type commands, and the server decides the consequences.

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
- `npm test` – run the Vitest suite

## Project Layout

- `src/api/` – fetch wrappers (`client.ts` handles auth headers and error messages, `shifts.ts` the game API)
- `src/hooks/useShift.ts` – owns the shift view and terminal scrollback
- `src/terminal/` – pure helpers: command echo/log lines, Tab completion
- `src/components/` – `Hud`, `Inbox`, `CommandInput`, layout shell
- `src/pages/` – `LoginPage` (sign in / create account) and `TerminalPage`
- `src/context/` – React context for session management

## How to play

Create an account, press **Start shift** and type `help`. Messages arrive as time passes: `read` one, then
`execute`, `deny`, `delay` or `investigate` it. `wait` lets time pass; `Tab` completes, arrow keys recall history.

## Next Steps

- Real-time message feed (SSE) instead of command-driven time
- Playwright end-to-end test of a full shift
- Decide React vs. the GDD's SvelteKit before the UI grows
