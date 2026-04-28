# PDF Processing — Delta For Legend And Detector Generalization

## ADDED Requirements

### Requirement: Vertical sub-clustering inside legend rows

Within each legend row band, the system SHALL split colored components
into sub-clusters by vertical gap and emit one template per sub-cluster,
so that multiple symbols stacked under a single text label become
separate templates.

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
- THEN the stored template bounding box matches the union of the
  sub-cluster's mask components, not the full row span

#### Scenario: Conservative split

- GIVEN a single symbol made of multiple closely spaced mask components
  (for example an outline plus an inner mark)
- WHEN extraction runs
- THEN the components remain in one sub-cluster
- AND only one template is emitted for the row

### Requirement: Plan-aware template diagnostics

After legend extraction, the system SHALL run a coarse template match
against the plan image and attach diagnostics to each extracted template
based on the resulting plan evidence.

#### Scenario: Count plan matches per template

- GIVEN a freshly extracted legend template
- WHEN refinement runs
- THEN the template diagnostics include the number of strong, deduplicated
  matches found on the plan
- AND the diagnostics field is optional in `TemplateInfo` so that existing
  clients keep working without changes

#### Scenario: Flag templates without plan evidence

- GIVEN an extracted template with zero strong plan matches
- WHEN refinement runs
- THEN the template is preserved
- AND its diagnostics include a low-confidence extraction flag

### Requirement: Adaptive matching thresholds

The detector SHALL choose the template-matching threshold from per-template
metrics (plan evidence count, mask density) instead of hardcoded keyword
lists in symbol names.

#### Scenario: Threshold from plan evidence

- GIVEN a template with many recorded plan matches in its diagnostics
- WHEN matching runs
- THEN a strict threshold is selected
- AND no decision branches on the symbol name string

#### Scenario: Threshold without diagnostics

- GIVEN a template without plan-evidence diagnostics (for example a
  user-uploaded template)
- WHEN matching runs
- THEN the threshold is derived from mask density

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

The system SHALL locate the legend using the `LEGENDA` text anchor,
group label text into rows, and extract per-row symbol templates by
sub-clustering colored mask components within each row band.

#### Scenario: Row-band components are sub-clustered before emitting templates

- WHEN row components are gathered for a label row
- THEN they are split into sub-clusters by vertical gap
- AND each sub-cluster emits its own template with a per-cluster bounding
  box and a deterministic label

#### Scenario: Text-based extraction is insufficient

- GIVEN row sub-clustering returns too few templates
- WHEN contour extraction is available
- THEN the system falls back to contour-based template extraction
