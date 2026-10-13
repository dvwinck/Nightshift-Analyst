## What and why

<!-- One logical change per PR. What changed and why. -->

## How it was verified

- [ ] `cd backend && ruff check app tests && pytest`
- [ ] `cd frontend && npm run build && npm test`
- [ ] Behavior change has a new or updated test (engine rules: `backend/tests/engine/`)

## Checklist

- [ ] No changes outside the scope of this PR (anything found on the side is listed below, not fixed)
- [ ] Game rules stay in `backend/app/engine/` as pure functions; routes only validate and shape
- [ ] Published content in `backend/content/` is append-only (no renamed ids or changed flags)
- [ ] No secrets, tokens or personal data in code, logs or fixtures
- [ ] README / CLAUDE.md updated if commands, behavior or architecture changed

## Out of scope, found on the side

<!-- Optional. Anything noticed but deliberately not changed. -->
