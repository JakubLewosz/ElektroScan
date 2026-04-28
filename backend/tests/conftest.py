from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.config import SESSIONS_DIR
from main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]
SAMPLE_PDF = BACKEND_DIR / "samples" / "plan.pdf"


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def uploaded_session(client: TestClient) -> Iterator[str]:
    with SAMPLE_PDF.open("rb") as handle:
        response = client.post(
            "/api/preview",
            files={"file": ("plan.pdf", handle, "application/pdf")},
        )
    assert response.status_code == 200
    session_id = response.json()["sessionId"]
    try:
        yield session_id
    finally:
        session_dir = SESSIONS_DIR / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)


def parse_sse_events(raw: str) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    for chunk in raw.replace("\r\n", "\n").split("\n\n"):
        event = "message"
        data: list[str] = []
        for line in chunk.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].lstrip())
        if data:
            events.append((event, "\n".join(data)))
    return events


def result_from_sse(raw: str) -> tuple[int, dict]:
    progress_count = 0
    result: dict | None = None
    for event, data in parse_sse_events(raw):
        if event == "progress":
            progress_count += 1
        elif event == "result":
            result = json.loads(data)
        elif event == "error":
            raise AssertionError(f"Unexpected SSE error: {data}")
    assert result is not None
    return progress_count, result
