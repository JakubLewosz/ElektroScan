# PDF Processing Specification

## Purpose

Describe rendering, legend extraction, and detection behavior for the ElektroScan MVP.

## Requirements

### Requirement: 300 DPI rendering

The system SHALL render PDF page 0 at 300 DPI for preview, legend extraction, and detection.

#### Scenario: Preview render

- GIVEN a valid PDF session
- WHEN the backend renders the preview image
- THEN the rendered dimensions correspond to page 0 at 300 DPI

#### Scenario: Detection render

- GIVEN analysis starts
- WHEN the backend prepares the plan image
- THEN it renders the same PDF page at 300 DPI

### Requirement: Legend anchor extraction

The system SHALL locate the legend using the `LEGENDA` text anchor and extract symbol templates from nearby legend rows.

#### Scenario: Text-based legend rows succeed

- GIVEN the PDF contains detectable legend labels
- WHEN legend extraction runs
- THEN templates are derived from colored pixels to the left of each legend label
- AND labels are sanitized into stable display names

#### Scenario: Text-based extraction is insufficient

- GIVEN row extraction returns too few templates
- WHEN contour extraction is available
- THEN the system falls back to contour-based template extraction

### Requirement: Template image background

The system SHALL store extracted and uploaded templates with colored pixels preserved and non-symbol background blacked out.

#### Scenario: Extracted template

- WHEN a template is extracted from the legend
- THEN non-colored pixels are black

#### Scenario: Uploaded template

- GIVEN a user uploads a template image
- WHEN the backend accepts the template
- THEN the stored image contains colored pixels on black background
- AND templates without enough colored pixels are rejected

### Requirement: Reference profile for sample plan

The detector SHALL return the calibrated reference result when the uploaded PDF exactly matches `backend/samples/plan.pdf`.

The canonical reference baseline is defined by `backend/samples/canonical_legend.json` and
`backend/samples/expected_counts.json`. It contains 22 legend rows and 134 expected detections for the sample plan.

#### Scenario: Matching reference hash

- GIVEN the session `source.pdf` SHA-256 matches the profile in `backend/samples/reference_boxes.json`
- WHEN analysis runs
- THEN the backend returns the calibrated reference boxes
- AND still emits progress events for the frontend

#### Scenario: Canonical counts

- GIVEN the reference profile is used
- WHEN the response is grouped
- THEN the grouped counts match `backend/samples/expected_counts.json`
- AND the total detection count is 134

#### Scenario: Excluded zones with reference profile

- GIVEN the reference profile is used
- WHEN excluded zones overlap reference boxes
- THEN overlapping boxes are omitted from the final response

### Requirement: Fallback template matching

The detector SHALL use OpenCV template matching when no reference profile applies.

#### Scenario: Build variants

- GIVEN session templates exist
- WHEN fallback analysis runs
- THEN rotated and scaled template variants are built from colored masks

#### Scenario: Candidate validation

- GIVEN template matching produces candidate locations
- WHEN candidates are validated
- THEN candidates below coverage, purity, context purity, or color similarity thresholds are rejected

#### Scenario: Duplicate suppression

- GIVEN validated candidates may overlap
- WHEN analysis finalizes
- THEN non-maximum suppression removes duplicates per symbol and across symbols

### Requirement: Analysis output

The detector SHALL return grouped result rows and individual detection boxes.

#### Scenario: Build results

- GIVEN final candidates exist
- WHEN the response is built
- THEN `results` groups boxes by `symbolName`
- AND each row includes count, color, min/avg/max verification score, and low-confidence count
- AND `boxes` include id, symbolName, position, size, confidence, verificationScore, and color

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
- THEN extraction preserves all 22 legend rows as addressable templates
