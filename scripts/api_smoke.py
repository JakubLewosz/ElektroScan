#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from urllib import error, request


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_API_BASE_URL = os.environ.get("ELEKTROSCAN_API_BASE_URL", "http://127.0.0.1:8010/api")
DEFAULT_PDF_PATH = ROOT_DIR / "backend" / "samples" / "plan.pdf"


def http_json(url: str, method: str = "GET", payload: object | None = None, timeout: int = 120) -> object:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    response = request.urlopen(request.Request(url, data=data, headers=headers, method=method), timeout=timeout)
    return json.loads(response.read().decode("utf-8"))


def upload_pdf(api_base_url: str, pdf_path: Path, timeout: int = 120) -> dict[str, object]:
    boundary = f"----elektroscan-{uuid.uuid4().hex}"
    pdf_bytes = pdf_path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("ascii"),
            f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"\r\n'.encode("utf-8"),
            b"Content-Type: application/pdf\r\n\r\n",
            pdf_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("ascii"),
        ]
    )
    req = request.Request(
        f"{api_base_url}/preview",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
    )
    response = request.urlopen(req, timeout=timeout)
    return json.loads(response.read().decode("utf-8"))


def parse_sse(raw: str) -> list[tuple[str, str]]:
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


def analyze(api_base_url: str, session_id: str, timeout: int = 180) -> tuple[int, dict[str, object]]:
    req = request.Request(
        f"{api_base_url}/analyze?session_id={session_id}",
        data=json.dumps({"excludedZones": [], "hiddenLayers": []}).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    response = request.urlopen(req, timeout=timeout)
    events = parse_sse(response.read().decode("utf-8"))
    result: dict[str, object] | None = None
    progress_count = 0
    for event, data in events:
        if event == "progress":
            progress_count += 1
        elif event == "result":
            result = json.loads(data)
        elif event == "error":
            raise RuntimeError(json.loads(data).get("message", "SSE analysis error"))
    if result is None:
        raise RuntimeError("SSE stream ended without result event")
    return progress_count, result


def main() -> int:
    parser = argparse.ArgumentParser(description="ElektroScan API smoke flow.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF_PATH)
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the newly created smoke-test session at the end. This deletes local generated session data.",
    )
    args = parser.parse_args()

    api_base_url = str(args.api_base_url).rstrip("/")
    pdf_path = args.pdf.resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    try:
        health = http_json(f"{api_base_url}/health")
        if health != {"status": "ok"}:
            raise RuntimeError(f"Unexpected health response: {health}")

        preview = upload_pdf(api_base_url, pdf_path)
        session_id = str(preview["sessionId"])
        if not str(preview.get("previewImage", "")).startswith("data:image/png;base64,"):
            raise RuntimeError("Preview image is not a PNG data URL")

        layers = http_json(f"{api_base_url}/layers?session_id={session_id}")
        templates = http_json(
            f"{api_base_url}/extract-legend?session_id={session_id}",
            method="POST",
            payload={"excludedZones": [], "hiddenLayers": []},
        )
        progress_count, analysis = analyze(api_base_url, session_id)
        boxes = analysis.get("boxes", [])
        results = analysis.get("results", [])

        print(f"health: {health['status']}")
        print(f"session: {session_id}")
        print(f"preview: {preview['pageSize']['width']}x{preview['pageSize']['height']}")
        print(f"layers: {len(layers)}")
        print(f"templates: {len(templates)}")
        print(f"progress events: {progress_count}")
        print(f"results: {len(results)}")
        print(f"boxes: {len(boxes)}")

        if len(boxes) != 134:
            raise RuntimeError(f"Expected 134 boxes for reference PDF, got {len(boxes)}")

        if args.clear:
            http_json(f"{api_base_url}/clear?session_id={session_id}", method="POST")
            print("cleared: yes")
        else:
            print("cleared: no")

    except error.URLError as exc:
        print(f"API smoke failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
