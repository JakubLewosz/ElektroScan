# ElektroScan Project Memory

Read these files before changing code:

- @AGENTS.md
- @README.md
- @openspec/HANDOFF.md
- @openspec/specs/pdf-processing/spec.md
- @openspec/specs/frontend-workflow/spec.md
- @openspec/specs/project-governance/spec.md

## Current Source Of Truth

- Canonical legend: `backend/samples/canonical_legend.json`
- Expected reference counts: `backend/samples/expected_counts.json`
- Calibrated reference boxes: `backend/samples/reference_boxes.json`
- Reference PDF: `backend/samples/plan.pdf`

The current accepted reference total is 134 detections.

Legend extraction returns all 22 canonical rows. Fallback detector totals are
recorded in `backend/samples/fallback_expected_counts.json`.

## Working Rules

- Keep implementation aligned with OpenSpec.
- If behavior changes, create a new change folder under `openspec/changes/<change-id>/` with proposal/tasks/spec deltas, then merge into `openspec/specs/` after archiving.
- Do not treat generated session data, frontend build output, or `node_modules` as source of truth.
- Run `./scripts/verify.sh` after code changes.

