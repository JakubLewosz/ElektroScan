# Agent Instructions

This project uses OpenSpec for persistent product and engineering context.

## Before Starting Work

- Read `openspec/README.md`.
- Read the relevant files under `openspec/specs/` before changing code.
- If the request changes behavior, create or update a change folder under `openspec/changes/<change-id>/` with:
  - `proposal.md`
  - `design.md` when technical trade-offs matter
  - `tasks.md`
  - `specs/<capability>/spec.md` deltas

## During Implementation

- Keep implementation aligned with the accepted specs.
- Mark completed tasks in `tasks.md` as work is finished.
- If code and spec diverge, update the spec or call out the mismatch.

## After Implementation

- Run the relevant backend and frontend checks.
- When the user considers a change complete, archive the change and fold the final requirements into `openspec/specs/`.
- Do not treat generated app state in `backend/data/sessions/`, `frontend/dist/`, or `node_modules/` as source-of-truth.
