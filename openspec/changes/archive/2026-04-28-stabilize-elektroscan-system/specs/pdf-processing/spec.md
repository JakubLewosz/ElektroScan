# PDF Processing Specification Delta

## ADDED Requirements

### Requirement: Measured fallback calibration

Fallback detector changes SHALL be evaluated with measurable reports instead of ad hoc visual inspection alone.

#### Scenario: Fallback benchmark run

- GIVEN the exact-reference profile is intentionally bypassed or unavailable
- WHEN fallback analysis runs on the reference PDF
- THEN the system records total detections, per-symbol counts, and deviation from the accepted fallback baseline

#### Scenario: Symbol naming mismatch

- GIVEN fallback extractor labels differ from reference JSON labels
- WHEN per-symbol deviation is calculated
- THEN the benchmark uses either an explicit alias map or an accepted fallback-label expected-count file

### Requirement: Preserve calibrated reference profile

Fallback detector tuning SHALL NOT break the exact-reference path.

#### Scenario: Reference hash matches

- GIVEN the uploaded PDF matches `backend/samples/reference_boxes.json`
- WHEN analysis runs after fallback tuning
- THEN the calibrated profile still returns the reference boxes unless a new spec explicitly replaces that profile

### Requirement: Canonical reference legend

The reference plan SHALL use the 22-row canonical legend and count baseline recorded in
`backend/samples/canonical_legend.json`.

#### Scenario: Canonical analysis total

- GIVEN `backend/samples/plan.pdf` matches the calibrated reference profile
- WHEN analysis runs
- THEN the backend returns 134 detection boxes
- AND the grouped counts match `backend/samples/expected_counts.json`

#### Scenario: Full legend extraction target

- GIVEN the reference PDF legend contains 22 rows
- WHEN legend extraction runs
- THEN extraction should preserve all 22 legend rows as addressable templates or documented zero-count reference rows
- AND missing extracted rows remain a calibration task before detector threshold tuning
