# ElektroScan Project Memory

Read these files before changing code:

- @AGENTS.md
- @README.md
- @openspec/HANDOFF.md
- @openspec/specs/pdf-processing/spec.md
- @openspec/specs/frontend-workflow/spec.md
- @openspec/changes/stabilize-elektroscan-system/tasks.md
- @openspec/changes/stabilize-elektroscan-system/design.md

## Current Source Of Truth

- Canonical legend: `backend/samples/canonical_legend.json`
- Expected reference counts: `backend/samples/expected_counts.json`
- Calibrated reference boxes: `backend/samples/reference_boxes.json`
- Reference PDF: `backend/samples/plan.pdf`

The current accepted reference total is 134 detections, not 138.

The legend has 22 canonical rows. Current extraction still returns 19 templates.
Preserve all 22 rows before tuning detector thresholds or NMS behavior.

## Working Rules

- Keep implementation aligned with OpenSpec.
- If behavior changes, update the relevant OpenSpec change or spec files.
- Do not treat generated session data, frontend build output, or `node_modules` as source of truth.
- Run `./scripts/verify.sh` after code changes.

