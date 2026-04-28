# Project Governance Specification Delta

## ADDED Requirements

### Requirement: Repository-local OpenSpec source of truth

The project SHALL keep current behavioral requirements under `openspec/specs/`.

#### Scenario: Agent starts a code change

- GIVEN a change request affects product behavior, backend contracts, frontend workflow, or detection output
- WHEN an agent starts implementation
- THEN the agent reads the relevant `openspec/specs/` files first
- AND keeps the implementation aligned with those requirements

### Requirement: Change folders for non-trivial work

The project SHALL use `openspec/changes/<change-id>/` for non-trivial proposed changes.

#### Scenario: New feature request

- GIVEN a request adds or changes non-trivial behavior
- WHEN the work is not an emergency fix
- THEN a change folder is created with `proposal.md`, `tasks.md`, and relevant spec deltas

### Requirement: Reference PDF priority

The project SHALL prioritize correctness on `backend/samples/plan.pdf` over broad generality.

#### Scenario: Generalization harms reference accuracy

- GIVEN a proposed generalized detector or UI workflow reduces correctness on `backend/samples/plan.pdf`
- WHEN the trade-off is identified
- THEN the generalized behavior is rejected or constrained
- AND the reference-plan behavior remains the acceptance baseline
