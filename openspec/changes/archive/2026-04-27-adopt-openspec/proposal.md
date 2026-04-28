# Adopt OpenSpec

## Why

The MVP has enough behavior to need durable context beyond chat history. OpenSpec gives the project a repository-local source of truth for current behavior and a lightweight workflow for future changes.

## What Changes

- Add OpenSpec instructions for agents.
- Add current source-of-truth specs for backend API, PDF processing, frontend workflow, session state, and project governance.
- Add a changes area for future proposals.
- Document the OpenSpec workflow in the root README.

## Scope

In scope:

- Documentation and workflow files.
- No runtime dependency changes.
- No backend or frontend behavior changes.

Out of scope:

- Installing the global OpenSpec CLI.
- Adding CI validation for OpenSpec.
- Reworking existing application architecture.

## Success Criteria

- A future agent can understand the MVP from `openspec/specs/`.
- A future non-trivial feature can start with `openspec/changes/<change-id>/`.
- Frontend and backend builds still pass after documentation changes.
