# ElektroScan

<p align="center">
  <a href="https://github.com/JakubLewosz/ElektroScan/actions/workflows/ci.yml">
    <img alt="ElektroScan CI workflow status" src="https://github.com/JakubLewosz/ElektroScan/actions/workflows/ci.yml/badge.svg" />
  </a>
  <img alt="Status: active development" src="https://img.shields.io/badge/status-active%20development-22C55E?style=flat-square" />
  <img alt="Repository scope: public showcase" src="https://img.shields.io/badge/scope-public%20showcase-38BDF8?style=flat-square" />
</p>

ElektroScan is a browser-based MVP for analysing electrical PDF plans and counting colour-coded symbols. It demonstrates a complete local workflow from PDF upload and legend extraction to computer-vision analysis and manual review of detected symbols.

> [!IMPORTANT]
> The public repository contains an earlier showcase version of ElektroScan. A substantially improved version is currently being developed privately by a two-person team.

This README describes only the implementation available in this public repository. It does not document the private version.

## Team and project origin

The original project brief was proposed by the director of Technikum Programistyczne INFOTECH in Białystok. ElektroScan was the main project of a 150-hour hybrid vocational software development internship based at the school from 27 April to 25 May 2026.

ElektroScan is developed by a two-person team. Both team members share responsibilities across backend development, frontend development, computer vision, testing, and documentation.

## Problem and purpose

Counting repeated electrical symbols on a PDF plan can require extensive manual inspection. The public ElektroScan prototype explores a reviewable workflow in which a user can:

- upload an electrical plan as a PDF;
- inspect its first page and control the visibility of PDF layers;
- extract symbol templates from the plan legend;
- run symbol analysis while receiving progress updates;
- review, confirm, reject, or reclassify detections;
- add manual detections and exclude selected plan areas.

## What the public version demonstrates

- Session-scoped PDF uploads, templates, and analysis state.
- Rendering of the first PDF page at 300 DPI with PyMuPDF.
- Legend extraction and fallback template matching based on coloured pixels with OpenCV and NumPy.
- A calibrated reference path for the included sample plan.
- REST endpoints and Server-Sent Events for analysis progress and results.
- An interactive plan canvas with pan, zoom, detection overlays, excluded zones, and manual boxes.
- Local review-state persistence scoped by session and analysis.
- Automated backend, frontend, browser, benchmark, and container-build checks.

## Public-version screenshot

![Public ElektroScan interface showing a PDF plan with detection overlays, controls, and review results](./docs/images/elektroscan-ui.jpg)

The screenshot represents the public showcase interface. Its current application text is in Polish.

## Architecture

- **Frontend — `frontend/`:** React and TypeScript application built with Vite and styled with Tailwind CSS. It manages the upload and review workflow, draws the interactive plan canvas, and stores review state in the browser.
- **Backend — `backend/`:** FastAPI and Pydantic service for PDF rendering, PDF-layer handling, legend-template management, analysis, and session-scoped file storage.
- **Analysis — `backend/core/`:** PyMuPDF renders the plan; OpenCV and NumPy support legend extraction and fallback template matching. Analysis progress and results are streamed to the frontend with Server-Sent Events.
- **Reference data — `backend/samples/`:** The included sample PDF has canonical legend, expected-count, context, and calibrated reference-box files used by the repository's regression benchmark.
- **Quality and delivery:** pytest, Ruff, Black, mypy, Playwright, Docker Compose, GitHub Actions, and a repository-level verification script.
- **Specifications — `openspec/`:** Current requirements and planned changes are recorded using OpenSpec.

## Technologies

| Area | Technologies |
| --- | --- |
| Backend and API | Python 3.12, FastAPI, Pydantic, Uvicorn, Server-Sent Events |
| Computer vision and documents | OpenCV, PyMuPDF, NumPy |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Testing and quality | pytest, Ruff, Black, mypy, Playwright |
| Delivery and documentation | Docker Compose, GitHub Actions, OpenSpec |

## Current public limitations

- The MVP is optimised for the repository's specific reference file, [`backend/samples/plan.pdf`](./backend/samples/plan.pdf), rather than for arbitrary electrical plans.
- When that exact sample file is analysed, the backend uses its calibrated reference profile. The accepted result of **134 detections applies only to this sample**; it is not an accuracy, precision, recall, or general-performance measurement.
- Automatic legend extraction currently returns 19 templates from the sample's 22 canonical legend rows. Preserving all 22 rows remains an open calibration task.
- Other PDFs use fallback OpenCV template matching. Its behaviour is still being calibrated and no general detection-quality claim is made.
- Only the first page of an uploaded PDF is processed.
- Working data is stored in local session directories. The public repository contains no user-account system, database persistence, or production deployment configuration.
- The public interface is currently in Polish.

## Setup

### Prerequisites

- Docker with Docker Compose, or
- Python 3.12 and Node.js 22 (the versions used by CI and the Docker images) for a manual setup.

### Docker Compose

```bash
git clone https://github.com/JakubLewosz/ElektroScan.git
cd ElektroScan
docker compose up -d --build
```

After startup:

- frontend: <http://127.0.0.1:5174/>
- backend health endpoint: <http://127.0.0.1:8010/api/health>

Stop the local stack with:

```bash
docker compose down
```

### Manual setup

Clone the repository, then start the backend:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

In a second terminal, start the frontend:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5174
```

Open <http://127.0.0.1:5174/> in a browser.

## Verification and testing

The repository provides one local verification command. Before running it, install the backend development requirements, frontend packages, and the Playwright Chromium browser:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

cd ../frontend
npm ci
npm run test:e2e:install

cd ..
./scripts/verify.sh
```

The script runs backend compilation, Ruff, Black, mypy, pytest, the reference-sample benchmark, frontend type checks and build, and Playwright end-to-end tests. The GitHub Actions workflow runs equivalent quality checks and also validates the Docker image builds.

To run the API smoke flow, start the backend on port `8010` and use:

```bash
backend/.venv/bin/python scripts/api_smoke.py
```

The fallback detector has a separate, slower benchmark:

```bash
cd backend
.venv/bin/python fallback_benchmark.py --strict
```

The benchmark result for 134 detections is scoped exclusively to the included reference sample and must not be interpreted as performance on other plans.
