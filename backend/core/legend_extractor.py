from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import fitz
import numpy as np

from core.config import (
    DPI,
    LEGEND_CLOSE_KERNEL,
    LEGEND_HSV_LOWER,
    LEGEND_HSV_UPPER,
    LEGEND_MIN_DENSITY,
    LEGEND_MIN_HEIGHT,
    LEGEND_MIN_WIDTH,
)
from core.models import Rect, TemplateInfo
from core.pdf_render import pdf_to_bgr
from core.storage import add_template_image, clear_templates, list_templates, sanitize_name


@dataclass(frozen=True)
class TextBlock:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str


@dataclass(frozen=True)
class LegendRow:
    center_y: float
    blocks: list[TextBlock]


@dataclass(frozen=True)
class MaskComponent:
    x: int
    y: int
    width: int
    height: int
    area: int
    center_x: float
    center_y: float


ROW_GROUP_TOLERANCE_PT = 4.0
ROW_BOUNDARY_MARGIN_PT = 2.5
SYMBOL_COMPONENT_MIN_AREA = 8
SYMBOL_CROP_PADDING_PX = 2


def _normalize_heading(value: str) -> str:
    return sanitize_name(value).replace("_", "").upper()


def _find_legend_anchor(page: fitz.Page) -> fitz.Rect:
    matches = page.search_for("LEGENDA")
    if matches:
        return matches[0]

    candidates: list[fitz.Rect] = []
    for block in page.get_text("blocks"):
        text = str(block[4])
        normalized = _normalize_heading(text)
        if "LEGENDA" in normalized or "LEGEND" in normalized:
            candidates.append(fitz.Rect(block[:4]))

    if not candidates:
        raise ValueError("Nie znaleziono slowa LEGENDA w PDF.")

    return sorted(candidates, key=lambda rect: (rect.y0, rect.x0))[0]


def _legend_clip(page: fitz.Page, anchor: fitz.Rect) -> fitz.Rect:
    page_rect = page.rect
    x0 = max(0, anchor.x0 - 35)
    y0 = max(0, anchor.y0 - 12)
    x1 = page_rect.x1
    y1 = min(page_rect.y1, anchor.y0 + page_rect.height * 0.45)
    return fitz.Rect(x0, y0, x1, y1)


def _load_text_blocks(pdf_path: Path, clip: fitz.Rect) -> list[TextBlock]:
    with fitz.open(pdf_path) as document:
        page = document.load_page(0)
        blocks: list[TextBlock] = []
        for raw in page.get_text("blocks"):
            rect = fitz.Rect(raw[:4])
            if not rect.intersects(clip):
                continue
            text = " ".join(str(raw[4]).split())
            if text:
                blocks.append(TextBlock(rect.x0, rect.y0, rect.x1, rect.y1, text))
        return blocks


def _rect_intersects(rect: Rect, x: int, y: int, w: int, h: int) -> bool:
    return not (x + w < rect.x or rect.x + rect.width < x or y + h < rect.y or rect.y + rect.height < y)


def _block_center_y(block: TextBlock) -> float:
    return (block.y0 + block.y1) / 2


def _group_text_rows(blocks: list[TextBlock], clip: fitz.Rect) -> list[LegendRow]:
    label_blocks = [
        block
        for block in blocks
        if "LEGENDA" not in block.text.upper() and block.x0 > clip.x0 + 8 and block.y0 > clip.y0 + 8
    ]
    label_blocks.sort(key=lambda block: (_block_center_y(block), block.x0))

    rows: list[LegendRow] = []
    for block in label_blocks:
        center_y = _block_center_y(block)
        if rows and abs(center_y - rows[-1].center_y) <= ROW_GROUP_TOLERANCE_PT:
            blocks_in_row = [*rows[-1].blocks, block]
            rows[-1] = LegendRow(
                center_y=sum(_block_center_y(item) for item in blocks_in_row) / len(blocks_in_row),
                blocks=blocks_in_row,
            )
            continue
        rows.append(LegendRow(center_y=center_y, blocks=[block]))

    return rows


def _main_label_block(row: LegendRow) -> TextBlock:
    return max(row.blocks, key=lambda block: (len(sanitize_name(block.text)), block.x0))


def _mask_components(mask: np.ndarray) -> list[MaskComponent]:
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    components: list[MaskComponent] = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if int(area) < SYMBOL_COMPONENT_MIN_AREA:
            continue
        components.append(
            MaskComponent(
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                area=int(area),
                center_x=float(centroids[index][0]),
                center_y=float(centroids[index][1]),
            )
        )
    return components


def _label_for_contour(
    blocks: list[TextBlock],
    clip: fitz.Rect,
    contour_x: int,
    contour_y: int,
    contour_w: int,
    contour_h: int,
    scale: float,
    index: int,
) -> str:
    contour_right_pdf = clip.x0 + (contour_x + contour_w) / scale
    contour_center_y_pdf = clip.y0 + (contour_y + contour_h / 2) / scale

    best: tuple[float, str] | None = None
    for block in blocks:
        if block.x0 < contour_right_pdf - 2:
            continue
        y_center = (block.y0 + block.y1) / 2
        distance = abs(y_center - contour_center_y_pdf)
        if distance > max(10, contour_h / scale * 1.8):
            continue
        if "LEGENDA" in block.text.upper():
            continue
        score = distance + max(0.0, contour_right_pdf - block.x0) * 0.1
        if best is None or score < best[0]:
            best = (score, block.text)

    if best is None:
        return f"symbol_{index:02d}"
    return sanitize_name(best[1], fallback=f"symbol_{index:02d}")


def _row_templates_from_text_blocks(
    legend: np.ndarray,
    mask: np.ndarray,
    blocks: list[TextBlock],
    clip: fitz.Rect,
    scale: float,
    clip_x_px: int,
    clip_y_px: int,
    excluded: list[Rect],
) -> list[tuple[int, int, int, int, str, np.ndarray]]:
    rows = _group_text_rows(blocks, clip)
    components = _mask_components(mask)
    items: list[tuple[int, int, int, int, str, np.ndarray]] = []
    for index, row in enumerate(rows):
        block = _main_label_block(row)
        previous_center = rows[index - 1].center_y if index > 0 else row.center_y - 8
        next_center = rows[index + 1].center_y if index + 1 < len(rows) else row.center_y + 14

        row_top_pdf = max(clip.y0, (previous_center + row.center_y) / 2 - ROW_BOUNDARY_MARGIN_PT)
        row_bottom_pdf = min(clip.y1, (row.center_y + next_center) / 2 + ROW_BOUNDARY_MARGIN_PT)
        label_left_px = int(round((block.x0 - clip.x0 - 2) * scale))
        label_left_px = max(1, min(label_left_px, legend.shape[1]))

        row_top = max(0.0, (row_top_pdf - clip.y0) * scale)
        row_bottom = min(float(legend.shape[0]), (row_bottom_pdf - clip.y0) * scale)
        if row_bottom <= row_top:
            continue

        row_components = [
            component
            for component in components
            if component.x < label_left_px and row_top <= component.center_y <= row_bottom
        ]
        if not row_components:
            continue

        cx = min(component.x for component in row_components)
        cy = min(component.y for component in row_components)
        cw = max(component.x + component.width for component in row_components) - cx
        ch = max(component.y + component.height for component in row_components) - cy
        if cw < LEGEND_MIN_WIDTH or ch < LEGEND_MIN_HEIGHT:
            continue

        absolute_x = clip_x_px + cx
        absolute_y = clip_y_px + row_top + cy
        if any(_rect_intersects(zone, absolute_x, absolute_y, cw, ch) for zone in excluded):
            continue

        pixel_count = sum(component.area for component in row_components)
        density = pixel_count / max(1, cw * ch)
        if density < LEGEND_MIN_DENSITY:
            continue

        source_y0 = max(0, cy - SYMBOL_CROP_PADDING_PX)
        source_y1 = min(legend.shape[0], cy + ch + SYMBOL_CROP_PADDING_PX)
        source_x0 = max(0, cx - SYMBOL_CROP_PADDING_PX)
        source_x1 = min(legend.shape[1], cx + cw + SYMBOL_CROP_PADDING_PX)
        roi = legend[source_y0:source_y1, source_x0:source_x1]
        roi_mask = mask[source_y0:source_y1, source_x0:source_x1]
        template = np.zeros_like(roi)
        template[roi_mask > 0] = roi[roi_mask > 0]
        label = sanitize_name(block.text, fallback=f"symbol_{len(items) + 1:02d}")
        items.append((absolute_y, absolute_x, cw, ch, label, template))

    return items


def extract_legend_templates(
    session_id: str,
    pdf_path: Path,
    excluded_zones: list[Rect] | None = None,
    hidden_layers: list[str] | None = None,
) -> list[TemplateInfo]:
    excluded = excluded_zones or []
    scale = DPI / 72

    with fitz.open(pdf_path) as document:
        page = document.load_page(0)
        anchor = _find_legend_anchor(page)
        clip = _legend_clip(page, anchor)
        clip_px = (
            int(round(clip.x0 * scale)),
            int(round(clip.y0 * scale)),
            int(round(clip.x1 * scale)),
            int(round(clip.y1 * scale)),
        )

    page_image = pdf_to_bgr(pdf_path, dpi=DPI, hidden_layers=hidden_layers)
    x0, y0, x1, y1 = clip_px
    x0 = max(0, min(x0, page_image.shape[1] - 1))
    y0 = max(0, min(y0, page_image.shape[0] - 1))
    x1 = max(x0 + 1, min(x1, page_image.shape[1]))
    y1 = max(y0 + 1, min(y1, page_image.shape[0]))
    legend = page_image[y0:y1, x0:x1]

    hsv = cv2.cvtColor(legend, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(LEGEND_HSV_LOWER), np.array(LEGEND_HSV_UPPER))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, LEGEND_CLOSE_KERNEL)
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    text_blocks = _load_text_blocks(pdf_path, clip)

    clear_templates(session_id)
    items = _row_templates_from_text_blocks(
        legend,
        mask,
        text_blocks,
        clip,
        scale,
        x0,
        y0,
        excluded,
    )

    if len(items) < 8:
        items = []
        for contour in contours:
            cx, cy, cw, ch = cv2.boundingRect(contour)
            if cw < LEGEND_MIN_WIDTH or ch < LEGEND_MIN_HEIGHT:
                continue
            if any(_rect_intersects(zone, x0 + cx, y0 + cy, cw, ch) for zone in excluded):
                continue

            tight_mask = mask[cy : cy + ch, cx : cx + cw]
            pixel_count = int(cv2.countNonZero(tight_mask))
            density = pixel_count / max(1, cw * ch)
            if density < LEGEND_MIN_DENSITY:
                continue

            pad = 2
            px0 = max(0, cx - pad)
            py0 = max(0, cy - pad)
            px1 = min(legend.shape[1], cx + cw + pad)
            py1 = min(legend.shape[0], cy + ch + pad)
            roi = legend[py0:py1, px0:px1]
            roi_mask = mask[py0:py1, px0:px1]
            template = np.zeros_like(roi)
            template[roi_mask > 0] = roi[roi_mask > 0]
            label = _label_for_contour(text_blocks, clip, cx, cy, cw, ch, scale, len(items) + 1)
            items.append((y0 + cy, x0 + cx, cw, ch, label, template))

    for _, _, _, _, label, template in sorted(items, key=lambda item: (item[0], item[1])):
        add_template_image(session_id, label, template)

    return list_templates(session_id)
