# Session State Specification

## Purpose

Describe how ElektroScan scopes files, templates, analysis state, and local review state.

## Requirements

### Requirement: Backend working data is session-scoped

The backend SHALL isolate uploads, templates, and snapshots by `sessionId`.

#### Scenario: New session

- WHEN a preview upload succeeds
- THEN the backend creates `backend/data/sessions/<session_id>/`
- AND creates `templates/` and `snapshots/` inside that session

#### Scenario: Template mutation

- GIVEN templates are renamed, deleted, uploaded, extracted, or cleared
- WHEN the mutation completes
- THEN only the active session's `templates/` directory and `templates.json` are affected

### Requirement: Session validation

The backend SHALL reject invalid or missing session identifiers.

#### Scenario: Invalid session format

- GIVEN `session_id` does not match the expected UUID-like format
- WHEN a session-scoped endpoint is called
- THEN the backend rejects the request

#### Scenario: Missing session directory

- GIVEN `session_id` has valid format but no stored session exists
- WHEN a session-scoped endpoint is called
- THEN the backend returns a not-found error

### Requirement: Analysis context

The analysis response SHALL include context describing how the result was generated.

#### Scenario: Result event

- WHEN analysis emits the final result
- THEN `analysisContext` includes `analysisId`, generation time, `sessionId`, source PDF name, hidden layers used, and excluded zones used

### Requirement: Frontend local persistence

The frontend SHALL scope local review state by both `sessionId` and `analysisId`.

#### Scenario: Store statuses

- GIVEN a session and analysis are active
- WHEN box statuses change
- THEN statuses are stored under a localStorage key containing the session and analysis ids

#### Scenario: Restore statuses

- GIVEN stored review state exists for a session and analysis
- WHEN the same analysis result is loaded
- THEN box statuses and hidden symbol types are restored from scoped localStorage keys

#### Scenario: New upload

- GIVEN a new PDF is uploaded
- WHEN the frontend receives a new session
- THEN prior review state is not applied to the new session unless its scoped key matches
