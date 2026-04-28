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
    PLAN_AWARE_DEDUP_RADIUS_FACTOR,
    PLAN_AWARE_MATCH_THRESHOLD,
    PLAN_AWARE_MAX_PEAKS,
    PLAN_AWARE_PLAN_HSV_LOWER,
    PLAN_AWARE_PLAN_HSV_UPPER,
)
from core.models import Rect, TemplateDiagnostics, TemplateInfo
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
# Some legend rows place the symbol flush against the label text with
# near-zero gap. Using center_x with this tolerance ensures components
# are matched even when their left edge slightly exceeds the label boundary.
SYMBOL_X_OVERHANG_PX = 40
# When multiple symbols share a single label row, vertical gaps larger
# than this fraction of the median symbol height split the row into
# separate templates. The threshold is intentionally conservative: a
# typical multi-component symbol (outline plus inner mark) has gaps
# well below the median symbol height, so we only split when the gap
# clearly exceeds one symbol height.
ROW_SUBCLUSTER_GAP_FACTOR = 1.2
ROW_SUBCLUSTER_MIN_GAP_PX = 12.0
# Each sub-cluster must occupy at least this fraction of LEGEND_MIN_HEIGHT
# to be emitted as a separate template — prevents tiny stray components
# being treated as second symbols.
ROW_SUBCLUSTER_MIN_HEIGHT_RATIO = 0.6


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


def _median_symbol_height(components: list[MaskComponent]) -> float:
    if not components:
        return 24.0
    heights = sorted(component.height for component in components)
    middle = heights[len(heights) // 2]
    return float(max(8, middle))


def _split_row_clusters(components: list[MaskComponent], median_symbol_height: float) -> list[list[MaskComponent]]:
    if not components:
        return []
    sorted_components = sorted(components, key=lambda component: component.center_y)
    gap_threshold = max(ROW_SUBCLUSTER_MIN_GAP_PX, median_symbol_height * ROW_SUBCLUSTER_GAP_FACTOR)
    clusters: list[list[MaskComponent]] = [[sorted_components[0]]]
    for component in sorted_components[1:]:
        previous_bottom = max(item.y + item.height for item in clusters[-1])
        gap = component.y - previous_bottom
        if gap > gap_threshold:
            clusters.append([component])
        else:
            clusters[-1].append(component)
    return _filter_substantive_clusters(clusters)


def _filter_substantive_clusters(
    clusters: list[list[MaskComponent]],
) -> list[list[MaskComponent]]:
    if len(clusters) <= 1:
        return clusters

    min_height = max(1, int(LEGEND_MIN_HEIGHT * ROW_SUBCLUSTER_MIN_HEIGHT_RATIO))
    substantive: list[list[MaskComponent]] = []
    leftover: list[MaskComponent] = []
    for cluster in clusters:
        cluster_top = min(component.y for component in cluster)
        cluster_bottom = max(component.y + component.height for component in cluster)
        cluster_height = cluster_bottom - cluster_top
        if cluster_height < min_height:
            leftover.extend(cluster)
            continue
        substantive.append(cluster)

    if not substantive:
        # Nothing met the substantive threshold — fall back to the union
        # of all components in the row so the row still emits one template.
        return [sum(clusters, [])]

    if leftover:
        # Attach leftover components to the nearest substantive cluster.
        for component in leftover:
            target = min(
                substantive,
                key=lambda existing: min(abs(component.center_y - item.center_y) for item in existing),
            )
            target.append(component)

    return substantive


def _next_unclaimed_row_label(rows: list[LegendRow], row_index: int, claimed_indices: set[int]) -> str | None:
    for offset in range(row_index + 1, len(rows)):
        if offset in claimed_indices:
            continue
        return _main_label_block(rows[offset]).text
    return None


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
    median_height = _median_symbol_height(components)
    items: list[tuple[int, int, int, int, str, np.ndarray]] = []
    rows_with_symbols: set[int] = set()
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
            if component.center_x < label_left_px + SYMBOL_X_OVERHANG_PX and row_top <= component.center_y <= row_bottom
        ]
        if not row_components:
            continue

        sub_clusters = _split_row_clusters(row_components, median_height)
        if not sub_clusters:
            continue

        rows_with_symbols.add(index)
        primary_label = sanitize_name(block.text, fallback=f"symbol_{len(items) + 1:02d}")
        next_label_text = _next_unclaimed_row_label(rows, index, rows_with_symbols)

        for sub_index, cluster in enumerate(sub_clusters):
            cx = min(component.x for component in cluster)
            cy = min(component.y for component in cluster)
            cw = max(component.x + component.width for component in cluster) - cx
            ch = max(component.y + component.height for component in cluster) - cy
            if cw < LEGEND_MIN_WIDTH or ch < LEGEND_MIN_HEIGHT:
                continue

            absolute_x = clip_x_px + cx
            absolute_y = clip_y_px + cy
            if any(_rect_intersects(zone, absolute_x, absolute_y, cw, ch) for zone in excluded):
                continue

            pixel_count = sum(component.area for component in cluster)
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

            if sub_index == 0:
                label = primary_label
            elif sub_index == 1 and next_label_text is not None:
                label = sanitize_name(next_label_text, fallback=f"{primary_label}_b")
            else:
                label = f"{primary_label}_b" if sub_index == 1 else f"{primary_label}_{chr(ord('b') + sub_index - 1)}"

            items.append((absolute_y, absolute_x, cw, ch, label, template))

    return items


def _plan_mask(plan_image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(plan_image, cv2.COLOR_BGR2HSV)
    return cv2.inRange(
        hsv,
        np.array(PLAN_AWARE_PLAN_HSV_LOWER),
        np.array(PLAN_AWARE_PLAN_HSV_UPPER),
    )


def _template_colored_mask(template: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
    return cv2.inRange(
        hsv,
        np.array(PLAN_AWARE_PLAN_HSV_LOWER),
        np.array(PLAN_AWARE_PLAN_HSV_UPPER),
    )


def _count_plan_matches(plan_mask: np.ndarray, template: np.ndarray) -> int:
    if template.size == 0:
        return 0
    template_mask = _template_colored_mask(template)
    if template_mask.shape[0] < 4 or template_mask.shape[1] < 4:
        return 0
    if int(cv2.countNonZero(template_mask)) < 4:
        return 0

    # Downscale both plan and template for diagnostic matching — accuracy
    # within +/- 1 instance is plenty for the low-confidence flag and the
    # speedup is substantial (~4x).
    scale = 0.5
    scaled_plan = cv2.resize(
        plan_mask,
        (max(1, int(plan_mask.shape[1] * scale)), max(1, int(plan_mask.shape[0] * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    scaled_template = cv2.resize(
        template_mask,
        (max(1, int(template_mask.shape[1] * scale)), max(1, int(template_mask.shape[0] * scale))),
        interpolation=cv2.INTER_NEAREST,
    )
    height, width = scaled_template.shape[:2]
    if height < 4 or width < 4:
        return 0
    if height >= scaled_plan.shape[0] or width >= scaled_plan.shape[1]:
        return 0

    response = cv2.matchTemplate(scaled_plan, scaled_template, cv2.TM_CCOEFF_NORMED)
    peaks_mask = (response >= PLAN_AWARE_MATCH_THRESHOLD) & (
        response == cv2.dilate(response, np.ones((3, 3), dtype=np.float32))
    )
    ys, xs = np.where(peaks_mask)
    if xs.size == 0:
        return 0

    scores = response[ys, xs]
    order = np.argsort(scores)[::-1]
    if order.size > PLAN_AWARE_MAX_PEAKS:
        order = order[:PLAN_AWARE_MAX_PEAKS]
    xs_sorted = xs[order]
    ys_sorted = ys[order]

    radius = max(1.0, max(width, height) * PLAN_AWARE_DEDUP_RADIUS_FACTOR)
    kept_x: list[float] = []
    kept_y: list[float] = []
    for x, y in zip(xs_sorted.tolist(), ys_sorted.tolist(), strict=False):
        if any(((x - kx) ** 2 + (y - ky) ** 2) ** 0.5 < radius for kx, ky in zip(kept_x, kept_y, strict=False)):
            continue
        kept_x.append(float(x))
        kept_y.append(float(y))
    return len(kept_x)


def _refine_templates_against_plan(
    plan_image: np.ndarray,
    items: list[tuple[int, int, int, int, str, np.ndarray]],
) -> list[tuple[int, int, int, int, str, np.ndarray, TemplateDiagnostics]]:
    plan_mask = _plan_mask(plan_image)
    refined: list[tuple[int, int, int, int, str, np.ndarray, TemplateDiagnostics]] = []
    for absolute_y, absolute_x, cw, ch, label, template in items:
        match_count = _count_plan_matches(plan_mask, template)
        diagnostics = TemplateDiagnostics(
            matchesOnPlan=match_count,
            lowConfidenceExtraction=match_count == 0,
        )
        refined.append((absolute_y, absolute_x, cw, ch, label, template, diagnostics))
    return refined


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

    refined = _refine_templates_against_plan(page_image, items)
    for _, _, _, _, label, template, diagnostics in sorted(refined, key=lambda entry: (entry[0], entry[1])):
        add_template_image(session_id, label, template, diagnostics=diagnostics)

    return list_templates(session_id)
