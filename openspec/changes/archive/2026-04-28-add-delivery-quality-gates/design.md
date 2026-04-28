# Design: Delivery Quality Gates

## Docker

Use two services:

- `backend`: FastAPI served by Uvicorn on port `8010`.
- `frontend`: Vite dev server on port `5174`.

The Compose stack is intended for local development parity, not production hardening. Backend session data is stored in a named volume so uploads survive container restarts during local work.

## Backend Quality

Use tools that are common in Python projects and lightweight enough for this MVP:

- `pytest` for tests.
- `httpx` for FastAPI test client support.
- `ruff` for linting and import ordering.
- `black` for formatting checks.
- `mypy` for static typing.

`mypy` starts permissive enough to be useful without forcing a full typing refactor.

## Frontend Quality

The current frontend already has TypeScript and build checks. Keep `npm run lint` as `tsc --noEmit` for now and run `npm run build` in CI.

## CI

GitHub Actions runs:

- backend install,
- backend lint/type/test/benchmark,
- frontend install,
- frontend lint/build.

Docker Compose build is included to ensure Dockerfiles remain valid.

## Trade-offs

- No E2E browser automation yet; API smoke tests cover the riskiest integration path first.
- Vite dev server is used in Docker for developer convenience.
- The reference benchmark remains the primary detector regression gate.
