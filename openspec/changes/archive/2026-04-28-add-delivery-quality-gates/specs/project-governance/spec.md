# Project Governance Specification Delta

## ADDED Requirements

### Requirement: Dockerized local startup

The project SHALL provide a Docker Compose setup that starts the application locally.

#### Scenario: Local Compose startup

- GIVEN Docker is installed
- WHEN a developer runs `docker compose up -d`
- THEN backend and frontend services start
- AND the frontend is reachable on the documented local port
- AND the backend health endpoint is reachable on the documented local port

### Requirement: Quality gates before delivery

The project SHALL provide repeatable quality checks for backend and frontend code.

#### Scenario: Local verification

- GIVEN dependencies are installed
- WHEN a developer runs the project verification command
- THEN backend linting, type checks, tests, reference benchmark, frontend checks, and E2E tests run

#### Scenario: CI verification

- GIVEN code is pushed to GitHub
- WHEN GitHub Actions runs
- THEN the same core quality gates run in CI
- AND Docker images are built to validate container definitions

### Requirement: Frontend E2E coverage

The project SHALL include browser-level E2E coverage for the core MVP workflow.

#### Scenario: Reference PDF user flow

- GIVEN backend and frontend services can start locally
- WHEN the E2E suite runs
- THEN it uploads `backend/samples/plan.pdf`
- AND verifies the plan preview canvas is usable
- AND verifies legend extraction returns the current extracted template baseline
- AND verifies analysis reports the canonical 134 detected boxes
