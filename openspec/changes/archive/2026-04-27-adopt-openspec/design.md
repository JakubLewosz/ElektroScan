# Design: Adopt OpenSpec

## Decision

Implement OpenSpec as repository-local Markdown structure without installing a global CLI.

## Rationale

- The project already has Node dependencies, but installing global software requires a separate user confirmation and is not necessary for keeping specs in-repo.
- OpenSpec's documented core model is lightweight: current specs in `openspec/specs/`, proposed work in `openspec/changes/`, and completed work in `openspec/changes/archive/`.
- The most valuable immediate outcome is durable requirements for the current ElektroScan MVP.

## Capability Split

- `backend-api` covers FastAPI contracts.
- `pdf-processing` covers rendering, legend extraction, and detection.
- `frontend-workflow` covers user-facing workflow and review tools.
- `session-state` covers session isolation and local persistence.
- `project-governance` covers how OpenSpec is used going forward.

## Trade-offs

- Manual Markdown structure cannot run `openspec validate` until the CLI is installed.
- The specs are still readable and useful for agents immediately.
- CLI installation can be added later as a separate change if desired.
