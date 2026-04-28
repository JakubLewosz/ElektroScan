from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import fitz
import pytest

from core.detector import analyze_session
from core.legend_extractor import (
    MaskComponent,
    _filter_substantive_clusters,
    _split_row_clusters,
    extract_legend_templates,
)
from core.storage import SESSIONS_DIR, create_session_dir, load_template_records


def _component(x: int, y: int, width: int, height: int) -> MaskComponent:
    return MaskComponent(
        x=x,
        y=y,
        width=width,
        height=height,
        area=width * height,
        center_x=float(x + width / 2),
        center_y=float(y + height / 2),
    )


class TestSplitRowClusters:
    def test_single_cluster_when_components_are_close(self) -> None:
        components = [_component(0, 10, 20, 12), _component(0, 24, 20, 12)]

        clusters = _split_row_clusters(components, median_symbol_height=20.0)

        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_splits_when_vertical_gap_exceeds_threshold(self) -> None:
        components = [_component(0, 0, 30, 20), _component(0, 60, 30, 20)]

        clusters = _split_row_clusters(components, median_symbol_height=20.0)

        assert len(clusters) == 2
        assert clusters[0][0].y == 0
        assert clusters[1][0].y == 60

    def test_returns_empty_for_no_components(self) -> None:
        assert _split_row_clusters([], median_symbol_height=20.0) == []


class TestFilterSubstantiveClusters:
    def test_keeps_single_cluster(self) -> None:
        cluster = [_component(0, 0, 30, 20)]

        result = _filter_substantive_clusters([cluster])

        assert result == [cluster]

    def test_merges_tiny_cluster_into_substantive_neighbour(self) -> None:
        big = [_component(0, 0, 30, 20)]
        tiny = [_component(0, 60, 4, 4)]

        result = _filter_substantive_clusters([big, tiny])

        assert len(result) == 1
        # Tiny cluster's component should have been folded into the big one.
        assert any(component.height == 4 for component in result[0])

    def test_falls_back_to_union_when_no_substantive_cluster(self) -> None:
        first = [_component(0, 0, 4, 4)]
        second = [_component(0, 60, 4, 4)]

        result = _filter_substantive_clusters([first, second])

        assert len(result) == 1
        assert len(result[0]) == 2


@pytest.fixture()
def synthetic_two_symbol_session(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    """Build a tiny PDF whose legend has two symbols stacked under one label.

    The PDF mimics a real legend layout: a `LEGENDA` heading on top, a single
    text label `Symbol A`, and two distinct colored shapes drawn one above
    the other in the symbol column. Without sub-clustering the extractor
    would merge both shapes into a single template.
    """

    pdf_path = tmp_path / "synthetic_legend.pdf"
    document = fitz.open()
    page = document.new_page(width=400, height=400)

    page.insert_text((40, 50), "LEGENDA", fontsize=14, color=(0, 0, 0))

    red = (1.0, 0.1, 0.1)
    page.draw_circle(fitz.Point(60, 110), 8, color=red, fill=red)
    page.draw_rect(fitz.Rect(50, 140, 70, 160), color=red, fill=red)

    page.insert_text((100, 130), "Symbol A", fontsize=12, color=(0, 0, 0))

    document.save(pdf_path)
    document.close()

    session_id, session_dir = create_session_dir()
    source_pdf = session_dir / "source.pdf"
    shutil.copyfile(pdf_path, source_pdf)

    try:
        yield session_id, source_pdf
    finally:
        target = SESSIONS_DIR / session_id
        if target.exists():
            shutil.rmtree(target)


def test_extract_legend_splits_two_symbols_under_one_label(
    synthetic_two_symbol_session: tuple[str, Path],
) -> None:
    session_id, source_pdf = synthetic_two_symbol_session

    templates = extract_legend_templates(session_id, source_pdf)

    # The fixture has a single label row but two distinct shapes; we expect
    # the extractor to emit two templates, not one merged template.
    assert len(templates) >= 2

    records = load_template_records(session_id)
    primary_labels = {record.display_name for record in records[:2]}
    # The first cluster receives the original label; the second falls back
    # to a derived label suffix because there is no second legend row.
    assert any(label.startswith("symbol_a") for label in primary_labels)


def test_fallback_analysis_runs_without_reference_profile(
    synthetic_two_symbol_session: tuple[str, Path],
) -> None:
    """Generalization sanity check: with no reference JSON profile, the
    fallback path still extracts templates, runs analysis, and returns a
    well-formed response on a synthetic plan that the calibrated profile
    cannot help with."""

    session_id, source_pdf = synthetic_two_symbol_session

    templates = extract_legend_templates(session_id, source_pdf)
    assert templates  # at least one template extracted

    progress: list[dict] = []
    response = analyze_session(
        session_id,
        source_pdf,
        excluded_zones=[],
        hidden_layers=[],
        on_progress=lambda event: progress.append(event.model_dump()),
        use_reference_profile=False,
    )

    assert len(progress) > 0
    assert sum(item.count for item in response.results) == len(response.boxes)
    assert any(template.diagnostics is not None for template in templates)
