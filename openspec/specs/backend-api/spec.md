# Backend API Specification

## Purpose

Describe the FastAPI contract used by the ElektroScan frontend.

## Requirements

### Requirement: API prefix and health

The backend SHALL expose JSON and SSE endpoints under `/api`.

#### Scenario: Health check

- WHEN a client requests `GET /api/health`
- THEN the backend responds with `{"status":"ok"}`

### Requirement: PDF preview session

The backend SHALL create an isolated session for every uploaded PDF preview.

#### Scenario: Valid PDF upload

- GIVEN a client uploads a non-empty PDF to `POST /api/preview`
- WHEN the backend can render page 0
- THEN it creates a session directory under `backend/data/sessions/<session_id>/`
- AND stores the upload as `source.pdf`
- AND returns `sessionId`, `fileName`, `previewImage`, and `pageSize`

#### Scenario: Invalid upload

- GIVEN a client uploads an empty or non-PDF file
- WHEN `POST /api/preview` is handled
- THEN the backend responds with an error instead of creating a usable preview

### Requirement: Native preview coordinates

The backend SHALL use native 300 DPI preview pixels for all rectangles exchanged with the frontend.

#### Scenario: Rectangle payloads

- GIVEN the frontend sends `excludedZones`
- WHEN `/api/extract-legend` or `/api/analyze` uses those zones
- THEN `x`, `y`, `width`, and `height` are interpreted as native preview pixels

#### Scenario: Detection boxes returned

- WHEN analysis returns `boxes`
- THEN every box coordinate is expressed in native preview pixels

### Requirement: PDF layers

The backend SHALL expose PDF layer state and allow preview rendering with hidden layers.

#### Scenario: Fetch layers

- GIVEN a valid session
- WHEN a client requests `GET /api/layers?session_id=<id>`
- THEN the backend returns layer names and visibility state

#### Scenario: Render preview with hidden layers

- GIVEN a valid session and `hiddenLayers`
- WHEN a client calls `POST /api/render-preview?session_id=<id>`
- THEN the backend renders page 0 at 300 DPI with those layers hidden
- AND returns the updated preview image, page size, and layer state

### Requirement: Session-scoped templates

The backend SHALL store templates per session, not globally.

#### Scenario: Extract legend

- GIVEN a valid session
- WHEN a client calls `POST /api/extract-legend?session_id=<id>`
- THEN existing session templates are cleared
- AND templates extracted from the PDF legend are stored under that session
- AND each template image keeps only colored symbol pixels on black background

#### Scenario: List templates

- GIVEN a valid session
- WHEN a client requests `GET /api/templates?session_id=<id>`
- THEN the backend returns each template's stable `name`, editable `displayName`, base64 PNG, width, and height

#### Scenario: Rename template

- GIVEN a valid session and template `name`
- WHEN a client calls `PATCH /api/templates/{template_name}?session_id=<id>` with `newName`
- THEN only `displayName` is changed
- AND the stable technical `name` remains unchanged
- AND duplicate names within the same session are rejected with conflict status

#### Scenario: Delete or clear templates

- GIVEN a valid session
- WHEN a client deletes one template or clears all templates
- THEN only templates in that session are removed

### Requirement: SSE analysis

The backend SHALL stream progress events before returning the final analysis result.

#### Scenario: Analyze valid session

- GIVEN a valid session and analysis payload
- WHEN a client calls `POST /api/analyze?session_id=<id>`
- THEN the backend responds as `text/event-stream`
- AND emits progress events with `stage`, `message`, and bounded `percent`
- AND emits one final `result` event containing analysis context, result rows, and detection boxes

#### Scenario: Analysis error

- GIVEN analysis fails
- WHEN the SSE stream is active
- THEN the backend emits an `error` event with a user-readable message

### Requirement: Clear session

The backend SHALL remove session working data when requested.

#### Scenario: Clear existing session

- GIVEN a valid session
- WHEN a client calls `POST /api/clear?session_id=<id>`
- THEN the backend removes that session directory
- AND returns `{"status":"ok"}`
