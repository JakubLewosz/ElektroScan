# PDF Processing — Delta For Legend And Detector Generalization

## ADDED Requirements

### Requirement: Symbol-first legend segmentation

The system SHALL segment legend symbols from the colored mask before
assigning text labels, so that legend rows are not the primary geometry.

#### Scenario: Two symbols stacked vertically under one label row

- GIVEN a legend in which two distinct symbols share the vertical span of
  a single text label
- WHEN legend extraction runs
- THEN both symbols are extracted as separate templates
- AND the upper symbol receives the original label
- AND the lower symbol receives a deterministic fallback label
  (label of the next legend row if unassigned, otherwise `<label>_b`)

#### Scenario: Tight bounding box per symbol

- GIVEN a legend symbol with surrounding whitespace inside its row
- WHEN extraction segments the symbol
- THEN the stored template bounding box matches the symbol footprint,
  not the row span

### Requirement: Plan-aware template refinement

After legend extraction, the system SHALL run a coarse template match
against the plan image and use the resulting clusters to refine each
extracted template.

#### Scenario: Tighten bounding box from plan evidence

- GIVEN an extracted template whose bounding box differs by more than
  30 % in area from the median bounding box of its strongest plan matches
- WHEN refinement runs
- THEN the template is re-cropped to the median plan footprint
- AND its colored mask is regenerated for the new crop

#### Scenario: Flag templates without plan evidence

- GIVEN an extracted template with zero strong plan matches
- WHEN refinement runs
- THEN the template is preserved
- AND its diagnostics include a low-confidence extraction flag

### Requirement: Adaptive matching thresholds

The detector SHALL choose the template-matching threshold from per-template
metrics (size, mask density, component count) instead of hardcoded keyword
lists in symbol names.

#### Scenario: Threshold from template metrics

- GIVEN a template with a small footprint and low component count
- WHEN matching runs
- THEN the strict or medium threshold is selected
- AND no decision branches on the symbol name string

#### Scenario: Reference profile unaffected

- GIVEN a session whose source PDF matches the calibrated reference profile
- WHEN analysis runs
- THEN the calibrated reference response is returned unchanged

### Requirement: Generalization smoke benchmark

The project SHALL provide a generalization smoke benchmark that runs
fallback detection without the reference JSON profile.

#### Scenario: Fallback on reference plan

- GIVEN `backend/samples/plan.pdf`
- WHEN the fallback benchmark runs with `use_reference_profile=False`
- THEN it reports per-symbol counts
- AND deviation from `backend/samples/fallback_expected_counts.json` is
  not worse than the recorded baseline

#### Scenario: Alternative plan smoke

- GIVEN an alternative PDF passed via `--alt-pdf`
- WHEN the fallback benchmark runs
- THEN extraction and analysis complete without exceptions
- AND the per-symbol counts are reported in the benchmark output

## MODIFIED Requirements

### Requirement: Legend anchor extraction

The system SHALL locate the legend using the `LEGENDA` text anchor and
extract symbol templates by clustering colored mask components, then
assigning the closest text label to each cluster.

#### Scenario: Symbol cluster precedes label assignment

- GIVEN the legend mask contains colored components
- WHEN extraction runs
- THEN components are first clustered into symbol candidates
- AND each cluster is paired with the closest legend label by vertical
  proximity, with tolerance derived from the median symbol height

#### Scenario: Text-based extraction is insufficient

- GIVEN cluster-based extraction returns too few templates
- WHEN contour extraction is available
- THEN the system falls back to contour-based template extraction
