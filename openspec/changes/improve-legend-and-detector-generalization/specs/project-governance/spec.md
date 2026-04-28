# Project Governance — Delta For Generalization Smoke

## ADDED Requirements

### Requirement: Generalization smoke gate

The project SHALL include a generalization smoke check exercising the
fallback detector path (no reference profile) on at least one PDF.

#### Scenario: Generalization smoke run

- GIVEN dependencies are installed
- WHEN a developer runs verification with `ELEKTROSCAN_GENERALIZATION_SMOKE=1`
- THEN the fallback detector runs against `backend/samples/plan.pdf`
- AND the deviation from `backend/samples/fallback_expected_counts.json`
  is reported
- AND the run is considered failed if deviation is worse than the recorded
  baseline

#### Scenario: Reference benchmark unaffected

- GIVEN the generalization smoke is enabled
- WHEN verification runs
- THEN the reference benchmark on `backend/samples/plan.pdf` still returns
  the canonical 134 detections via the calibrated profile
