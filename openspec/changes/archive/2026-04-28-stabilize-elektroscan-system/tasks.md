# Tasks

## 1. Verification Backbone

- [x] Add a project-level verification script or documented command set.
- [x] Include backend compile check.
- [x] Include reference benchmark check.
- [x] Include frontend build check.
- [x] Add an API smoke flow for upload, layers, templates, analysis, and clear session.

## 2. Backend Contract Coverage

- [x] Add backend test dependencies only if needed and approved by the project.
- [x] Test `GET /api/health`.
- [x] Test `POST /api/preview` with `backend/samples/plan.pdf`.
- [x] Test `GET /api/layers`.
- [x] Test `POST /api/extract-legend`.
- [x] Test `POST /api/analyze` SSE result shape.
- [x] Test template rename, delete, and clear behavior.
- [x] Test `POST /api/clear`.

## 3. Frontend Maintainability

- [x] Extract canvas interaction logic from `App.tsx` without behavior changes.
- [x] Extract sidebar action surface from `App.tsx`.
- [x] Extract results/review surface from `App.tsx`.
- [x] Preserve canvas pan, modifier zoom, and zoom controls.
- [x] Preserve localStorage scoping by `sessionId` and `analysisId`.

## 4. Detector Calibration

- [x] Decide whether fallback benchmark names should use current extractor labels or aliases to reference JSON names.
- [x] Add a measurable fallback benchmark report.
- [x] Improve legend extraction for missing expected symbol rows.
- [x] Preserve all 22 canonical legend rows during extraction, not only the 19 currently extracted templates.
- [x] Tune candidate validation thresholds per measured deviation.
- [x] Tune NMS behavior for over-detected large green oprawa and button symbols.
- [x] Keep exact reference profile behavior unchanged.
- [x] Apply first reference JSON label corrections: `04` detections become `05`, and box `(2742, 975)` becomes `06`.
- [x] Replace reference JSON names/counts with the canonical 22-row legend baseline and 134 expected detections.

## 5. Product Workflow Hardening

- [x] Improve upload and backend-unavailable error recovery.
- [x] Make template lifecycle states clearer.
- [x] Add durable user-facing analysis failure states.
- [x] Verify review slideshow with keyboard and mouse workflows.
- [x] Verify canvas navigation on desktop.
- [x] Verify canvas navigation on narrow viewport.
- [x] Add per-box copyable diagnostic logs for reference JSON correction before detector engine edits.

Local note: Playwright E2E verifies desktop and narrow-viewport canvas pan/zoom, scoped localStorage, upload retry, analysis retry, template lifecycle states, and review slideshow keyboard/mouse controls.
