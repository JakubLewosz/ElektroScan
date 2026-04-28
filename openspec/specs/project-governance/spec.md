# Project Governance Specification

## Purpose

Define how ElektroScan uses OpenSpec so future changes preserve durable context and stay aligned with the MVP goal.

## Requirements

### Requirement: Repository-local OpenSpec source of truth

The project SHALL keep current behavioral requirements under `openspec/specs/`.

#### Scenario: Agent starts a code change

- GIVEN a change request affects product behavior, backend contracts, frontend workflow, or detection output
- WHEN an agent starts implementation
- THEN the agent reads the relevant `openspec/specs/` files first
- AND keeps the implementation aligned with those requirements

#### Scenario: Existing behavior is documented

- GIVEN a feature exists in the MVP
- WHEN its expected behavior matters for future changes
- THEN the feature is described as requirements and scenarios in `openspec/specs/`

### Requirement: Change folders for non-trivial work

The project SHALL use `openspec/changes/<change-id>/` for non-trivial proposed changes.

#### Scenario: New feature request

- GIVEN a request adds or changes non-trivial behavior
- WHEN the work is not an emergency fix
- THEN a change folder is created with `proposal.md`, `tasks.md`, and relevant spec deltas

#### Scenario: Technical uncertainty exists

- GIVEN a change has meaningful architecture trade-offs
- WHEN a change folder is created
- THEN `design.md` records the chosen approach and rejected alternatives

### Requirement: Reference PDF priority

The project SHALL prioritize correctness on `backend/samples/plan.pdf` over broad generality.

#### Scenario: Generalization harms reference accuracy

- GIVEN a proposed generalized detector or UI workflow reduces correctness on `backend/samples/plan.pdf`
- WHEN the trade-off is identified
- THEN the generalized behavior is rejected or constrained
- AND the reference-plan behavior remains the acceptance baseline

### Requirement: System-wide verification baseline

Every non-trivial code change SHALL preserve a documented verification baseline.

#### Scenario: Backend or detector change

- GIVEN a change modifies backend endpoints, PDF processing, template extraction, or detection
- WHEN implementation is complete
- THEN backend compile checks pass
- AND the reference benchmark is run
- AND any benchmark regression is reported before final delivery

#### Scenario: Frontend change

- GIVEN a change modifies React, TypeScript, API client code, or canvas behavior
- WHEN implementation is complete
- THEN the frontend build passes
- AND the affected workflow is manually or programmatically smoke-tested when practical

### Requirement: OpenSpec task tracking

System-wide work SHALL be tracked through OpenSpec task lists.

#### Scenario: Work begins under an active change

- GIVEN an active change folder exists
- WHEN a task is implemented
- THEN the corresponding checkbox in `tasks.md` is updated
- AND unfinished tasks remain unchecked

### Requirement: Reference benchmark protection

The reference benchmark SHALL remain the primary regression gate for the MVP.

#### Scenario: Benchmark regression

- GIVEN `backend/samples/plan.pdf` previously returned the canonical 134 detections
- WHEN a change causes a different total or coordinate deviation
- THEN the change is considered incomplete unless the spec explicitly changes the expected baseline

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
