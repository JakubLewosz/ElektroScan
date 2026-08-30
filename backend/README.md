# ElektroScan backend

The FastAPI service for the public ElektroScan showcase. It manages session-scoped PDF uploads, first-page rendering, PDF layers, legend-template extraction and management, plan analysis, and streamed progress updates.

See the [project README](../README.md) for the public-version disclosure, team context, architecture, complete setup, and current limitations.

## API scope

- `GET /api/health` — return the service health status.
- `POST /api/preview` — store a PDF, create a local session, and render its first page.
- `GET /api/layers` — list PDF layers for the active session.
- `POST /api/render-preview` — render the plan with selected layers hidden.
- `POST /api/extract-legend` — extract symbol templates from the PDF legend.
- `GET /api/templates` — list session templates.
- `POST /api/templates/upload` — add a custom template image.
- `PATCH /api/templates/{template_name}` — change a template's display name.
- `DELETE /api/templates/{template_name}` — remove one template.
- `DELETE /api/templates` — clear all templates in the active session.
- `POST /api/analyze` — analyse the plan and stream progress and results with Server-Sent Events.
- `POST /api/clear` — remove the local session data.

## Current scope

- PDF rendering and analysis use page 0 at 300 DPI.
- The exact included sample plan uses its calibrated reference profile; other PDFs use fallback OpenCV template matching.
- The accepted 134-detection result applies only to the included reference sample and is not a general quality metric.
- Session data is stored on the local filesystem and is not intended as production persistence.

## Run locally

From the `backend` directory:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

Health endpoint:

```text
GET http://127.0.0.1:8010/api/health
```

## Verification

From the repository root, after installing the frontend packages and Playwright Chromium browser:

```bash
./scripts/verify.sh
```

With the backend already running on port `8010`, run the standalone API smoke flow with:

```bash
backend/.venv/bin/python scripts/api_smoke.py
```
