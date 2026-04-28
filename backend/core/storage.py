from __future__ import annotations

import base64
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import HTTPException

from core.config import SESSIONS_DIR
from core.models import TemplateInfo

TEMPLATE_METADATA_FILE = "templates.json"
POLISH_ASCII_TRANSLATION = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ź": "Z",
        "Ż": "Z",
    }
)


@dataclass(frozen=True)
class TemplateRecord:
    name: str
    display_name: str
    file_name: str


def create_session_dir() -> tuple[str, Path]:
    session_id = str(uuid4())
    session_dir = SESSIONS_DIR / session_id
    (session_dir / "templates").mkdir(parents=True, exist_ok=False)
    (session_dir / "snapshots").mkdir(parents=True, exist_ok=False)
    return session_id, session_dir


def get_session_dir(session_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9-]{36}", session_id):
        raise HTTPException(status_code=400, detail="Nieprawidlowy session_id.")

    session_dir = SESSIONS_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Nie znaleziono sesji.")

    return session_dir


def get_source_pdf(session_id: str) -> Path:
    source_path = get_session_dir(session_id) / "source.pdf"
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Sesja nie zawiera source.pdf.")
    return source_path


def get_templates_dir(session_id: str) -> Path:
    templates_dir = get_session_dir(session_id) / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def sanitize_name(value: str, fallback: str = "symbol") -> str:
    translated = value.translate(POLISH_ASCII_TRANSLATION)
    ascii_text = unicodedata.normalize("NFKD", translated).encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.strip().lower()).strip("_")
    return safe or fallback


def load_template_records(session_id: str) -> list[TemplateRecord]:
    metadata_path = get_templates_dir(session_id) / TEMPLATE_METADATA_FILE
    if not metadata_path.exists():
        return []

    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    return [
        TemplateRecord(
            name=str(item["name"]),
            display_name=str(item.get("displayName") or item["name"]),
            file_name=str(item.get("fileName") or f"{item['name']}.png"),
        )
        for item in data
    ]


def save_template_records(session_id: str, records: list[TemplateRecord]) -> None:
    metadata_path = get_templates_dir(session_id) / TEMPLATE_METADATA_FILE
    metadata_path.write_text(
        json.dumps(
            [
                {"name": record.name, "displayName": record.display_name, "fileName": record.file_name}
                for record in records
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def next_template_name(records: list[TemplateRecord], display_name: str) -> str:
    base = sanitize_name(display_name)
    existing = {record.name for record in records}
    index = len(records) + 1
    while True:
        candidate = f"{index:02d}_{base}"
        if candidate not in existing:
            return candidate
        index += 1


def add_template_image(session_id: str, display_name: str, image: np.ndarray) -> TemplateRecord:
    records = load_template_records(session_id)
    name = next_template_name(records, display_name)
    file_name = f"{name}.png"
    path = get_templates_dir(session_id) / file_name

    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Nie udalo sie zakodowac template'u PNG.")

    path.write_bytes(encoded.tobytes())
    record = TemplateRecord(name=name, display_name=sanitize_name(display_name), file_name=file_name)
    records.append(record)
    save_template_records(session_id, records)
    return record


def list_templates(session_id: str) -> list[TemplateInfo]:
    templates_dir = get_templates_dir(session_id)
    templates: list[TemplateInfo] = []

    for record in load_template_records(session_id):
        path = templates_dir / record.file_name
        if not path.exists():
            continue

        data = path.read_bytes()
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if image is None:
            continue

        templates.append(
            TemplateInfo(
                name=record.name,
                displayName=record.display_name,
                imgBase64="data:image/png;base64," + base64.b64encode(data).decode("ascii"),
                width=int(image.shape[1]),
                height=int(image.shape[0]),
            )
        )

    return templates


def read_template_image(session_id: str, record: TemplateRecord) -> np.ndarray:
    path = get_templates_dir(session_id) / record.file_name
    data = path.read_bytes()
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Nie mozna odczytac template'u {record.name}.")
    return image


def rename_template(session_id: str, template_name: str, new_name: str) -> None:
    records = load_template_records(session_id)
    normalized = sanitize_name(new_name)
    existing = {
        value for record in records if record.name != template_name for value in (record.name, record.display_name)
    }
    if normalized in existing:
        raise HTTPException(status_code=409, detail="Nazwa template'u juz istnieje.")

    updated: list[TemplateRecord] = []
    found = False
    for record in records:
        if record.name == template_name:
            updated.append(TemplateRecord(record.name, normalized, record.file_name))
            found = True
        else:
            updated.append(record)

    if not found:
        raise HTTPException(status_code=404, detail="Nie znaleziono template'u.")

    save_template_records(session_id, updated)


def delete_template(session_id: str, template_name: str) -> None:
    records = load_template_records(session_id)
    templates_dir = get_templates_dir(session_id)
    updated: list[TemplateRecord] = []
    found = False

    for record in records:
        if record.name == template_name:
            found = True
            path = templates_dir / record.file_name
            if path.exists():
                path.unlink()
        else:
            updated.append(record)

    if not found:
        raise HTTPException(status_code=404, detail="Nie znaleziono template'u.")

    save_template_records(session_id, updated)


def clear_templates(session_id: str) -> None:
    templates_dir = get_templates_dir(session_id)
    for path in templates_dir.glob("*.png"):
        path.unlink()
    save_template_records(session_id, [])
