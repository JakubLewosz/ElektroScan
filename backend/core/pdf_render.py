from __future__ import annotations

import base64
from pathlib import Path

import cv2
import fitz
import numpy as np

from core.config import DPI
from core.models import LayerInfo


def _apply_hidden_layers(document: fitz.Document, hidden_layers: list[str] | None) -> None:
    hidden = set(hidden_layers or [])
    if not hidden:
        return

    for item in document.layer_ui_configs():
        name = str(item.get("text", ""))
        if name in hidden and not item.get("locked", False):
            document.set_layer_ui_config(int(item["number"]), action=2)


def pdf_to_bgr(
    pdf_path: Path,
    dpi: int = DPI,
    hidden_layers: list[str] | None = None,
) -> np.ndarray:
    with fitz.open(pdf_path) as document:
        if document.page_count < 1:
            raise ValueError("PDF nie zawiera zadnych stron.")

        _apply_hidden_layers(document, hidden_layers)
        page = document.load_page(0)
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        rgb = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height,
            pixmap.width,
            pixmap.n,
        )

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def get_pdf_layers(pdf_path: Path, hidden_layers: list[str] | None = None) -> list[LayerInfo]:
    hidden = set(hidden_layers or [])
    with fitz.open(pdf_path) as document:
        ui_layers = document.layer_ui_configs()
        if ui_layers:
            return [
                LayerInfo(
                    name=str(item.get("text", "")),
                    visible=bool(item.get("on", True)) and str(item.get("text", "")) not in hidden,
                )
                for item in ui_layers
                if item.get("type") in {"checkbox", "radiobox"} and item.get("text")
            ]

        ocgs = document.get_ocgs()
        return [
            LayerInfo(
                name=str(value.get("name", f"Layer {xref}")),
                visible=bool(value.get("on", True)) and str(value.get("name", "")) not in hidden,
            )
            for xref, value in ocgs.items()
        ]


def bgr_to_png_data_url(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Nie udalo sie zakodowac podgladu PNG.")

    return "data:image/png;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")
