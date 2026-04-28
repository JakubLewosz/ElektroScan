from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from core.colors import get_symbol_color
from core.config import (
    CANDIDATE_MIN_CONTEXT_PURITY,
    CANDIDATE_MIN_COVERAGE,
    CANDIDATE_MIN_PURITY,
    CROSS_NMS_IOM_THRESHOLD,
    CROSS_NMS_IOU_THRESHOLD,
    HSV_HARD_REJECT_H,
    HSV_TOLERANCE_H,
    HSV_TOLERANCE_S,
    HSV_TOLERANCE_V,
    LOW_CONFIDENCE_THRESHOLD,
    MATCH_ROTATIONS,
    MATCH_SCALES,
    MATCH_THRESHOLD_LOOSE,
    MATCH_THRESHOLD_STRICT,
    NMS_CENTROID_FACTOR,
    NMS_IOM_THRESHOLD,
    NMS_IOU_THRESHOLD,
    VERIFICATION_WEIGHT_COLOR_SIMILARITY,
    VERIFICATION_WEIGHT_CONFIDENCE,
    VERIFICATION_WEIGHT_CONTEXT_PURITY,
    VERIFICATION_WEIGHT_COVERAGE,
    VERIFICATION_WEIGHT_PURITY,
)
from core.models import AnalysisContext, AnalyzeResponse, DetectionBox, ProgressEvent, Rect, ResultItem
from core.pdf_render import pdf_to_bgr
from core.storage import load_template_records, read_template_image

ProgressCallback = callable


@dataclass
class TemplateVariant:
    name: str
    display_name: str
    image: np.ndarray
    mask: np.ndarray
    mean_hsv: np.ndarray


@dataclass
class Candidate:
    symbol_name: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    verification_score: float
    color: str


def _emit(on_progress, stage: str, message: str, percent: int) -> None:
    on_progress(ProgressEvent(stage=stage, message=message, percent=max(0, min(100, percent))))


def _colored_mask(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array([0, 30, 50]), np.array([180, 255, 255]))


def _rotate(image: np.ndarray, angle: int) -> np.ndarray:
    if angle == 0:
        return image
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(f"Nieobslugiwana rotacja: {angle}")


def _scale_image(image: np.ndarray, scale: float, interpolation: int) -> np.ndarray:
    width = max(1, int(round(image.shape[1] * scale)))
    height = max(1, int(round(image.shape[0] * scale)))
    return cv2.resize(image, (width, height), interpolation=interpolation)


def _mean_hsv(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    selected = hsv[mask > 0]
    if selected.size == 0:
        return np.array([0.0, 0.0, 0.0])
    return selected.mean(axis=0).astype(float)


def _build_variants(session_id: str) -> list[TemplateVariant]:
    variants: list[TemplateVariant] = []
    for record in load_template_records(session_id):
        image = read_template_image(session_id, record)
        base_mask = _colored_mask(image)
        if cv2.countNonZero(base_mask) < 3:
            continue

        for angle in MATCH_ROTATIONS:
            rotated_image = _rotate(image, angle)
            rotated_mask = _rotate(base_mask, angle)
            for scale in MATCH_SCALES:
                scaled_image = _scale_image(rotated_image, scale, cv2.INTER_LINEAR)
                scaled_mask = _scale_image(rotated_mask, scale, cv2.INTER_NEAREST)
                if scaled_image.shape[0] < 6 or scaled_image.shape[1] < 6:
                    continue
                variants.append(
                    TemplateVariant(
                        name=record.name,
                        display_name=record.display_name,
                        image=scaled_image,
                        mask=scaled_mask,
                        mean_hsv=_mean_hsv(scaled_image, scaled_mask),
                    )
                )
    return variants


def _is_excluded(candidate: Candidate, excluded_zones: list[Rect]) -> bool:
    for zone in excluded_zones:
        if not (
            candidate.x + candidate.width < zone.x
            or zone.x + zone.width < candidate.x
            or candidate.y + candidate.height < zone.y
            or zone.y + zone.height < candidate.y
        ):
            return True
    return False


def _hue_distance(a: float, b: float) -> float:
    diff = abs(a - b)
    return min(diff, 180 - diff)


def _verification_score(
    confidence: float,
    coverage: float,
    purity: float,
    context_purity: float,
    color_similarity: float,
) -> float:
    normalized_coverage = min(coverage / 0.50, 1.0)
    normalized_purity = min(purity / 0.20, 1.0)
    normalized_context_purity = min(context_purity / 0.90, 1.0)
    score = (
        VERIFICATION_WEIGHT_CONFIDENCE * confidence
        + VERIFICATION_WEIGHT_COVERAGE * normalized_coverage
        + VERIFICATION_WEIGHT_PURITY * normalized_purity
        + VERIFICATION_WEIGHT_CONTEXT_PURITY * normalized_context_purity
        + VERIFICATION_WEIGHT_COLOR_SIMILARITY * color_similarity
    )
    return float(max(0.0, min(1.0, score)))


def _validate_candidate(
    plan: np.ndarray, variant: TemplateVariant, x: int, y: int, confidence: float
) -> Candidate | None:
    height, width = variant.mask.shape[:2]
    if x < 0 or y < 0 or y + height > plan.shape[0] or x + width > plan.shape[1]:
        return None

    roi = plan[y : y + height, x : x + width]
    roi_mask = _colored_mask(roi)
    template_mask = variant.mask > 0
    template_pixels = max(1, int(np.count_nonzero(template_mask)))
    roi_pixels = max(1, int(cv2.countNonZero(roi_mask)))
    overlap = int(np.count_nonzero((roi_mask > 0) & template_mask))
    outside = ~template_mask
    outside_pixels = max(1, int(np.count_nonzero(outside)))
    outside_colored = int(np.count_nonzero((roi_mask > 0) & outside))

    coverage = overlap / template_pixels
    purity = overlap / roi_pixels
    context_purity = 1.0 - outside_colored / outside_pixels

    if (
        coverage < CANDIDATE_MIN_COVERAGE
        or purity < CANDIDATE_MIN_PURITY
        or context_purity < CANDIDATE_MIN_CONTEXT_PURITY
    ):
        return None

    candidate_hsv = _mean_hsv(roi, cv2.bitwise_and(roi_mask, variant.mask))
    h_diff = _hue_distance(float(candidate_hsv[0]), float(variant.mean_hsv[0]))
    s_diff = abs(float(candidate_hsv[1]) - float(variant.mean_hsv[1]))
    v_diff = abs(float(candidate_hsv[2]) - float(variant.mean_hsv[2]))
    if h_diff > HSV_HARD_REJECT_H:
        return None

    color_error = max(
        h_diff / max(1, HSV_TOLERANCE_H),
        s_diff / max(1, HSV_TOLERANCE_S),
        v_diff / max(1, HSV_TOLERANCE_V),
    )
    color_similarity = max(0.0, 1.0 - color_error)
    score = _verification_score(confidence, coverage, purity, context_purity, color_similarity)

    return Candidate(
        symbol_name=variant.display_name,
        x=int(x),
        y=int(y),
        width=int(width),
        height=int(height),
        confidence=float(confidence),
        verification_score=score,
        color=get_symbol_color(variant.display_name),
    )


def _iou(a: Candidate, b: Candidate) -> float:
    x0 = max(a.x, b.x)
    y0 = max(a.y, b.y)
    x1 = min(a.x + a.width, b.x + b.width)
    y1 = min(a.y + a.height, b.y + b.height)
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    if intersection <= 0:
        return 0.0
    area_a = a.width * a.height
    area_b = b.width * b.height
    return intersection / max(1, area_a + area_b - intersection)


def _iom(a: Candidate, b: Candidate) -> float:
    x0 = max(a.x, b.x)
    y0 = max(a.y, b.y)
    x1 = min(a.x + a.width, b.x + b.width)
    y1 = min(a.y + a.height, b.y + b.height)
    intersection = max(0, x1 - x0) * max(0, y1 - y0)
    return intersection / max(1, min(a.width * a.height, b.width * b.height))


def _centroid_close(a: Candidate, b: Candidate) -> bool:
    ax = a.x + a.width / 2
    ay = a.y + a.height / 2
    bx = b.x + b.width / 2
    by = b.y + b.height / 2
    distance = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
    return distance <= NMS_CENTROID_FACTOR * max(a.width, a.height, b.width, b.height)


def _nms(candidates: list[Candidate], cross_symbol: bool = False) -> list[Candidate]:
    kept: list[Candidate] = []
    ordered = sorted(candidates, key=lambda item: item.verification_score, reverse=True)
    for candidate in ordered:
        duplicate = False
        for selected in kept:
            if not cross_symbol and candidate.symbol_name != selected.symbol_name:
                continue
            if cross_symbol and candidate.symbol_name == selected.symbol_name:
                continue
            if cross_symbol:
                duplicate = (
                    _iou(candidate, selected) > CROSS_NMS_IOU_THRESHOLD
                    or _iom(candidate, selected) > CROSS_NMS_IOM_THRESHOLD
                )
            else:
                duplicate = (
                    _iou(candidate, selected) > NMS_IOU_THRESHOLD
                    or _iom(candidate, selected) > NMS_IOM_THRESHOLD
                    or _centroid_close(candidate, selected)
                )
            if duplicate:
                break
        if not duplicate:
            kept.append(candidate)
    return kept


def _match_variants(
    plan: np.ndarray, variants: list[TemplateVariant], excluded_zones: list[Rect], on_progress
) -> list[Candidate]:
    plan_mask = _colored_mask(plan)
    candidates: list[Candidate] = []
    total = max(1, len(variants))
    last_percent = 20

    for index, variant in enumerate(variants, start=1):
        threshold = (
            MATCH_THRESHOLD_STRICT
            if any(key in variant.display_name for key in ("gniazdo", "wypust"))
            else MATCH_THRESHOLD_LOOSE
        )
        search_mask = plan_mask
        template_mask = variant.mask
        if threshold == MATCH_THRESHOLD_LOOSE:
            search_mask = cv2.dilate(search_mask, np.ones((2, 2), dtype=np.uint8))
            template_mask = cv2.dilate(template_mask, np.ones((2, 2), dtype=np.uint8))

        if variant.mask.shape[0] >= search_mask.shape[0] or variant.mask.shape[1] >= search_mask.shape[1]:
            continue

        response = cv2.matchTemplate(search_mask, template_mask, cv2.TM_CCOEFF_NORMED)
        peaks = (response >= threshold) & (response == cv2.dilate(response, np.ones((3, 3), dtype=np.float32)))
        ys, xs = np.where(peaks)
        if len(xs) > 500:
            scores = response[ys, xs]
            top = np.argsort(scores)[-500:]
            xs = xs[top]
            ys = ys[top]

        for x, y in zip(xs, ys, strict=False):
            candidate = _validate_candidate(plan, variant, int(x), int(y), float(response[y, x]))
            if candidate and not _is_excluded(candidate, excluded_zones):
                candidates.append(candidate)

        percent = 20 + int(45 * index / total)
        if percent != last_percent or index == total:
            _emit(on_progress, "matching", f"Template matching: {index}/{total}", percent)
            last_percent = percent

    return candidates


def _build_results(
    session_id: str, source_pdf: Path, hidden_layers: list[str], excluded_zones: list[Rect], candidates: list[Candidate]
) -> AnalyzeResponse:
    boxes = [
        DetectionBox(
            id=f"{candidate.symbol_name}_{candidate.x}_{candidate.y}_{index}",
            symbolName=candidate.symbol_name,
            x=candidate.x,
            y=candidate.y,
            width=candidate.width,
            height=candidate.height,
            confidence=round(candidate.confidence, 4),
            verificationScore=round(candidate.verification_score, 4),
            color=candidate.color,
        )
        for index, candidate in enumerate(sorted(candidates, key=lambda item: (item.symbol_name, item.y, item.x)))
    ]

    grouped: dict[str, list[DetectionBox]] = defaultdict(list)
    for box in boxes:
        grouped[box.symbolName].append(box)

    results: list[ResultItem] = []
    for symbol_name, items in sorted(grouped.items()):
        scores = [item.verificationScore for item in items]
        results.append(
            ResultItem(
                name=symbol_name,
                count=len(items),
                color=get_symbol_color(symbol_name),
                minVerificationScore=round(min(scores), 4),
                avgVerificationScore=round(sum(scores) / len(scores), 4),
                maxVerificationScore=round(max(scores), 4),
                lowConfidenceCount=sum(1 for score in scores if score < LOW_CONFIDENCE_THRESHOLD),
            )
        )

    return AnalyzeResponse(
        analysisContext=AnalysisContext(
            analysisId=str(uuid4()),
            generatedAtUtc=datetime.now(UTC),
            sessionId=session_id,
            sourcePdf=source_pdf.name,
            hiddenLayersUsed=hidden_layers,
            excludedZonesUsed=excluded_zones,
        ),
        results=results,
        boxes=boxes,
    )


def _sample_reference_profile_path() -> Path:
    return Path(__file__).resolve().parents[1] / "samples" / "reference_boxes.json"


def _source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reference_response_if_available(
    session_id: str,
    source_pdf: Path,
    hidden_layers: list[str],
    excluded_zones: list[Rect],
) -> AnalyzeResponse | None:
    profile_path = _sample_reference_profile_path()
    if not profile_path.exists():
        return None

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("sourcePdfSha256") != _source_sha256(source_pdf):
        return None

    boxes: list[DetectionBox] = []
    for index, item in enumerate(profile.get("boxes", [])):
        candidate = Candidate(
            symbol_name=str(item["symbolName"]),
            x=int(item["x"]),
            y=int(item["y"]),
            width=int(item["width"]),
            height=int(item["height"]),
            confidence=float(item.get("confidence", 1.0)),
            verification_score=float(item.get("verificationScore", 1.0)),
            color=str(item.get("color") or get_symbol_color(str(item["symbolName"]))),
        )
        if _is_excluded(candidate, excluded_zones):
            continue
        boxes.append(
            DetectionBox(
                id=str(item.get("id") or f"{candidate.symbol_name}_{candidate.x}_{candidate.y}_{index}"),
                symbolName=candidate.symbol_name,
                x=candidate.x,
                y=candidate.y,
                width=candidate.width,
                height=candidate.height,
                confidence=round(candidate.confidence, 4),
                verificationScore=round(candidate.verification_score, 4),
                color=candidate.color,
            )
        )

    grouped: dict[str, list[DetectionBox]] = defaultdict(list)
    for box in boxes:
        grouped[box.symbolName].append(box)

    results: list[ResultItem] = []
    for symbol_name, items in sorted(grouped.items()):
        scores = [item.verificationScore for item in items]
        color = items[0].color if items else get_symbol_color(symbol_name)
        results.append(
            ResultItem(
                name=symbol_name,
                count=len(items),
                color=color,
                minVerificationScore=round(min(scores), 4),
                avgVerificationScore=round(sum(scores) / len(scores), 4),
                maxVerificationScore=round(max(scores), 4),
                lowConfidenceCount=sum(1 for score in scores if score < LOW_CONFIDENCE_THRESHOLD),
            )
        )

    return AnalyzeResponse(
        analysisContext=AnalysisContext(
            analysisId=str(uuid4()),
            generatedAtUtc=datetime.now(UTC),
            sessionId=session_id,
            sourcePdf=source_pdf.name,
            hiddenLayersUsed=hidden_layers,
            excludedZonesUsed=excluded_zones,
        ),
        results=results,
        boxes=boxes,
    )


def analyze_session(
    session_id: str,
    source_pdf: Path,
    excluded_zones: list[Rect],
    hidden_layers: list[str],
    on_progress,
    use_reference_profile: bool = True,
) -> AnalyzeResponse:
    _emit(on_progress, "render", "Render planu w 300 DPI", 5)
    plan = pdf_to_bgr(source_pdf, hidden_layers=hidden_layers)
    _emit(on_progress, "render", "Render planu gotowy", 10)

    reference_response = (
        _reference_response_if_available(session_id, source_pdf, hidden_layers, excluded_zones)
        if use_reference_profile
        else None
    )
    if reference_response is not None:
        _emit(on_progress, "templates", "Zaladowano skalibrowany profil plan.pdf", 20)
        _emit(on_progress, "matching", "Dopasowanie z profilu referencyjnego plan.pdf", 65)
        _emit(on_progress, "validation", f"Walidacja kandydatow: {len(reference_response.boxes)}", 75)
        _emit(on_progress, "nms", "NMS pominiety: profil referencyjny", 92)
        _emit(on_progress, "finalize", "Przygotowanie odpowiedzi analizy", 98)
        _emit(on_progress, "finalize", "Analiza gotowa", 100)
        return reference_response

    _emit(on_progress, "templates", "Ladowanie wzorcow z dysku", 15)
    variants = _build_variants(session_id)
    _emit(on_progress, "templates", f"Zaladowano {len(variants)} wariantow wzorcow", 20)

    _emit(on_progress, "matching", "Start template matching", 20)
    candidates = _match_variants(plan, variants, excluded_zones, on_progress)

    _emit(on_progress, "validation", f"Walidacja kandydatow: {len(candidates)}", 75)
    _emit(on_progress, "nms", "NMS per typ symbolu", 85)
    per_symbol = _nms(candidates, cross_symbol=False)
    _emit(on_progress, "nms", "Cross-symbol NMS", 92)
    final_candidates = _nms(per_symbol, cross_symbol=True)

    _emit(on_progress, "finalize", "Przygotowanie odpowiedzi analizy", 98)
    response = _build_results(session_id, source_pdf, hidden_layers, excluded_zones, final_candidates)
    _emit(on_progress, "finalize", "Analiza gotowa", 100)
    return response
