# Frontend Workflow Specification

## Purpose

Describe the React workflow for uploading, reviewing, and correcting ElektroScan detections.

## Requirements

### Requirement: Three-column work surface

The frontend SHALL present controls, plan preview, and results as separate working areas.

#### Scenario: Initial screen

- WHEN no PDF is loaded
- THEN upload and action controls are visible
- AND the center area shows an empty preview placeholder
- AND the results panel waits for analysis data

### Requirement: PDF upload workflow

The frontend SHALL upload a selected PDF and initialize session-scoped state from the backend response.

#### Scenario: Upload succeeds

- GIVEN the user selects a PDF
- WHEN `/api/preview`, `/api/layers`, and `/api/templates` succeed
- THEN the preview image, layers, templates, and session id are stored in UI state
- AND prior analysis, boxes, review states, hidden symbol types, excluded zones, and focus are cleared

#### Scenario: Upload fails

- GIVEN upload or preview rendering fails
- WHEN the frontend receives an error
- THEN a user-readable error status is shown

### Requirement: Layer controls

The frontend SHALL let the user hide or show PDF layers and refresh the preview.

#### Scenario: Toggle layer

- GIVEN a session is active
- WHEN a layer checkbox changes
- THEN the frontend calls `/api/render-preview` with the updated hidden layer list
- AND replaces the preview image and layer state with the backend response

### Requirement: Legend and analysis actions

The frontend SHALL expose actions to extract legend templates and analyze the plan.

#### Scenario: Extract legend

- GIVEN a session is active
- WHEN the user starts legend extraction
- THEN the frontend sends excluded zones and hidden layers
- AND replaces the template list with the response

#### Scenario: Analyze plan

- GIVEN a session is active
- WHEN the user starts analysis
- THEN the frontend consumes SSE progress and heartbeat updates
- AND stores the final analysis response when the result event arrives
- AND reports an error if the stream closes without a result

### Requirement: Canvas navigation

The frontend SHALL allow normal navigation around large plan images.

#### Scenario: Scroll and trackpad movement

- GIVEN a preview is loaded
- WHEN the user scrolls normally over the preview
- THEN the scroll container pans the plan instead of forcing zoom

#### Scenario: Modifier zoom

- GIVEN a preview is loaded
- WHEN the user scrolls with Ctrl, Meta, or Alt pressed
- THEN the preview zoom changes around the pointer location

#### Scenario: Drag pan

- GIVEN the canvas mode is `idle`
- WHEN the user drags the plan
- THEN the scroll position changes according to drag distance

#### Scenario: Zoom controls

- GIVEN a preview is loaded
- WHEN the user uses zoom controls
- THEN the preview can be enlarged, reduced, or fit to the visible canvas area

### Requirement: Review and correction

The frontend SHALL let the user inspect, confirm, reject, reclassify, and manually add detections.

#### Scenario: Box status

- GIVEN analysis boxes are visible
- WHEN a box is confirmed or rejected
- THEN the status is stored locally for the active analysis
- AND rejected boxes are removed from result counts

#### Scenario: Manual box

- GIVEN analysis results contain at least one symbol type
- WHEN the user draws a manual rectangle in manual mode
- THEN a confirmed manual detection is added for the selected symbol type

#### Scenario: Excluded zone

- GIVEN the user draws a rectangle in exclude mode
- WHEN the rectangle is large enough
- THEN the excluded zone is stored and sent on subsequent legend extraction or analysis requests

#### Scenario: Slideshow review

- GIVEN a symbol type has active boxes
- WHEN slideshow review starts
- THEN boxes of that symbol type are ordered by low verification score first
- AND keyboard review can advance, confirm, reject, or exit

### Requirement: Results panel

The frontend SHALL derive visible result counts from current boxes and review statuses.

#### Scenario: Rejected boxes

- GIVEN some boxes have status `rejected`
- WHEN result rows are rendered
- THEN rejected boxes are excluded from counts and score aggregates

#### Scenario: Hidden symbol type

- GIVEN the user hides a symbol type
- WHEN boxes are rendered on the canvas
- THEN boxes for that symbol type are not visible
- AND result data remains available in the panel

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
