# Add Delivery Quality Gates

## Why

ElektroScan needs the same delivery basics expected from production projects: Dockerized local startup, linting, automated tests, and CI. These are required to keep the app runnable outside one developer machine and to catch regressions before they reach users.

## What Changes

- Add Dockerfiles for backend and frontend.
- Add `docker-compose.yml` so the project starts with `docker compose up -d`.
- Add backend lint/type tooling and tests.
- Add frontend lint/type/build checks.
- Add GitHub Actions workflow for CI.
- Wire these checks into the existing verification script.

## Scope

In scope:

- Local Docker Compose runtime.
- Backend unit/API contract tests.
- Python linting, formatting checks, and type checks.
- Frontend TypeScript build/lint.
- CI workflow for pull requests and pushes.

Out of scope:

- Production deployment manifests.
- Database services.
- Authentication or multi-user runtime.
- Container registry publishing.

## Success Criteria

- `docker compose up -d` starts backend and frontend services.
- Backend tests cover the reference PDF smoke flow and API contracts.
- `./scripts/verify.sh` runs backend quality checks, benchmark, and frontend build.
- GitHub Actions mirrors the local verification baseline.
