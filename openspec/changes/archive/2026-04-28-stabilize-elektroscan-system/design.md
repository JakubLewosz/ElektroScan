# Design: Stabilize ElektroScan System

## System Strategy

Treat the current MVP as the protected baseline. The system can evolve, but every change must preserve:

- reference PDF benchmark correctness,
- backend API compatibility unless the spec says otherwise,
- canvas review workflow usability,
- session-scoped data isolation.

## Work Phases

### Phase 1: Verification Backbone

Add repeatable checks for:

- backend import/compile health,
- API smoke flow,
- reference benchmark,
- frontend typecheck/build.

This phase should produce a small script or documented command set that can be run before and after changes.

### Phase 2: Backend Contract Tests

Cover the main API paths with tests:

- health,
- preview upload,
- layers,
- templates,
- analyze SSE result,
- session clearing.

Tests should use the reference PDF and avoid depending on generated session history.

### Phase 3: Frontend Surface Decomposition

Move behavior out of the monolithic `App.tsx` gradually:

- API state and analysis state,
- canvas interaction state,
- sidebar actions,
- results panel.

Each extraction must preserve current behavior and pass the same frontend build.

### Phase 4: Detector Calibration

Convert fallback detector tuning into a measured process:

- define accepted symbol-name mapping or accepted fallback benchmark labels,
- measure per-symbol deviations,
- tune extraction, validation, and NMS in small changes,
- keep the calibrated exact-reference profile intact.

Decision: fallback benchmark uses current extractor labels with
`backend/samples/fallback_expected_counts.json` as the accepted baseline. This keeps raw fallback behavior
measurable without forcing temporary aliases to the calibrated reference JSON names while those names are still
being corrected from copied box logs.

Legend extraction now groups text blocks into PDF rows and crops only the colored connected components assigned to
each row. This replaces broad row-band crops and keeps adjacent legend symbols out of templates. The reference legend
currently yields 19 precise templates.

Canonical reference decision: the user-provided legend is the source of truth for `backend/samples/plan.pdf`.
It has 22 rows, but the expected detections total 134 because rows `01`, `02`, `03`, `04`, `08`, `15`, `16`,
`17`, `18`, `20`, `21`, and `22` have zero occurrences on the plan. This baseline is stored in
`backend/samples/canonical_legend.json` and `backend/samples/expected_counts.json`; `reference_boxes.json` must use
canonical names with numeric prefixes from that legend.

### Phase 5: Product Hardening

Polish the workflows that affect repeated use:

- robust upload and retry states,
- clearer template lifecycle,
- safe local review persistence,
- consistent canvas controls,
- durable error reporting.

## Acceptance Commands

At minimum, system changes should run:

```bash
cd backend
.venv/bin/python -m compileall main.py core
.venv/bin/python benchmark.py

cd ../frontend
npm run build
```

When API behavior changes, also run an API smoke flow against the local backend.

## Trade-offs

- Generic detection quality is not optimized before the reference path is protected.
- The frontend should be refactored incrementally, not rewritten.
- OpenSpec docs are kept in-repo even without requiring global CLI installation.
