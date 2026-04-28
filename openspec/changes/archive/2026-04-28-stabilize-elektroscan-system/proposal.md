# Stabilize ElektroScan System

## Why

ElektroScan MVP now works for the reference PDF, but the system needs a structured path from MVP toward a maintainable product. The most important risks are insufficient automated verification, a monolithic frontend surface, weak fallback detector calibration for non-reference inputs, and scattered acceptance criteria.

This change makes OpenSpec the operating layer for system-wide development.

## What Changes

- Establish a system quality baseline for every future change.
- Add explicit benchmark and smoke-test expectations.
- Define a staged roadmap for backend, frontend, detection, and review workflow hardening.
- Add spec deltas for quality gates, fallback detector calibration, and frontend maintainability.

## Scope

In scope:

- Test and verification strategy.
- Backend API contract checks.
- Reference PDF benchmark preservation.
- Fallback detector calibration path.
- Frontend component and state boundaries.
- Canvas navigation and review workflow reliability.

Out of scope for this change:

- Cost estimate features.
- PDF/XLSX export.
- Multi-user accounts.
- Database persistence.
- Full generic CAD/PDF understanding.

## Success Criteria

- The reference PDF benchmark stays at the canonical 134/134 detections from `backend/samples/canonical_legend.json`.
- A single documented verification path exists for backend and frontend.
- Future changes have clear OpenSpec tasks before implementation.
- The fallback detector has a measurable calibration workflow instead of ad hoc threshold edits.
- The frontend can be refactored incrementally without losing current UI behavior.
