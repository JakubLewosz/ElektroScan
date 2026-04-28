# AI Handoff Notes

## Startup Context

ElektroScan is a React/Vite + FastAPI MVP for counting electrical symbols on
`backend/samples/plan.pdf`. The project uses OpenSpec as persistent context.

Before changing code, read:

- `AGENTS.md`
- `openspec/README.md`
- `openspec/specs/pdf-processing/spec.md`
- `openspec/specs/frontend-workflow/spec.md`
- `openspec/changes/stabilize-elektroscan-system/tasks.md`
- `openspec/changes/stabilize-elektroscan-system/design.md`

## Current Source Of Truth

- Canonical legend: `backend/samples/canonical_legend.json`
- Expected reference counts: `backend/samples/expected_counts.json`
- Calibrated reference boxes: `backend/samples/reference_boxes.json`
- Reference PDF: `backend/samples/plan.pdf`

The current accepted reference total is 134 detections, not 138.

The user-provided legend has 22 rows. Current extraction still returns 19 templates; preserving all 22 rows is an
open task and should be fixed before detector threshold/NMS tuning.

## Verification

Run the standard gate after code changes:

```bash
./scripts/verify.sh
```

Optional slower fallback detector benchmark:

```bash
cd backend
.venv/bin/python fallback_benchmark.py --strict
```

Docker verification is still pending on a Docker-enabled machine.
