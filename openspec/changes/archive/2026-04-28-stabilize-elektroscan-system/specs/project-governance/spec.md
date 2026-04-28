# Project Governance Specification Delta

## ADDED Requirements

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
