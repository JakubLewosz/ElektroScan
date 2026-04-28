# Frontend Workflow Specification Delta

## ADDED Requirements

### Requirement: Incremental frontend decomposition

The frontend SHALL be decomposed from `App.tsx` incrementally while preserving current behavior.

#### Scenario: Extract canvas behavior

- GIVEN canvas interaction logic is moved into a component or hook
- WHEN the refactor is complete
- THEN pan, modifier zoom, fit-to-view, excluded zones, manual boxes, and detection box interactions behave as before

#### Scenario: Extract results behavior

- GIVEN result and review logic is moved into a component or hook
- WHEN the refactor is complete
- THEN rejected boxes remain excluded from derived counts
- AND hidden symbol types still affect only canvas visibility

### Requirement: User workflow smoke checks

Frontend changes SHALL include a smoke check for the affected user workflow.

#### Scenario: Upload workflow changes

- GIVEN a change touches upload, preview, layer, or template UI
- WHEN the change is complete
- THEN the upload-to-preview path is smoke-tested with the reference PDF when practical

#### Scenario: Canvas workflow changes

- GIVEN a change touches canvas navigation or interaction mode logic
- WHEN the change is complete
- THEN pan, zoom, and drawing modes are smoke-tested when practical
