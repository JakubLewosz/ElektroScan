# Tasks

## Docker

- [x] Add backend Dockerfile.
- [x] Add frontend Dockerfile.
- [x] Add root `docker-compose.yml`.
- [x] Document `docker compose up -d`.
- [ ] Verify Docker config or build when Docker is available.

Local note: Docker is not installed in this environment, so Compose verification is deferred to a Docker-enabled machine or CI.

## Backend Quality

- [x] Add backend dev/test requirements.
- [x] Add pytest configuration.
- [x] Add API contract tests.
- [x] Add lint/type commands to verification script.
- [x] Keep reference benchmark at canonical 134/134.

## Frontend Quality

- [x] Preserve frontend lint command.
- [x] Preserve frontend build command.
- [x] Include frontend checks in local verification.
- [x] Add Playwright E2E dependencies and browser install command.
- [x] Add E2E workflow test for upload, canvas navigation, legend extraction, and analysis.
- [x] Include E2E tests in local verification.

## CI

- [x] Add GitHub Actions workflow.
- [x] Run backend lint/type/test/benchmark in CI.
- [x] Run frontend lint/build in CI.
- [x] Run Playwright E2E in CI.
- [x] Build Docker images in CI.
