# OpenSpec for ElektroScan

OpenSpec keeps the intended behavior of ElektroScan in the repository.

## Structure

- `specs/` is the current source of truth for shipped behavior.
- `changes/` is for proposed or in-progress changes.
- `changes/archive/` stores completed change records.

## Workflow

1. Create a change folder: `openspec/changes/<change-id>/`.
2. Write `proposal.md`, optional `design.md`, `tasks.md`, and spec deltas.
3. Implement the tasks against the specs.
4. Verify the app.
5. Archive the change and merge final requirements into `openspec/specs/`.

## Local Convention

ElektroScan is an MVP optimized for the reference PDF at `backend/samples/plan.pdf`.
Specs should preserve that priority. Generalization is only valid when it does not reduce correctness on the reference plan.
