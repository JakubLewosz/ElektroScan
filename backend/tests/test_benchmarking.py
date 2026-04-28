from __future__ import annotations

from core.benchmarking import compare_counts, summarize_rows


def test_compare_counts_reports_missing_extra_and_deviation() -> None:
    rows = compare_counts({"a": 4, "b": 2}, {"a": 3, "c": 1})
    by_name = {row.symbol_name: row for row in rows}

    assert by_name["a"].expected_count == 4
    assert by_name["a"].detected_count == 3
    assert by_name["a"].deviation == 0.25
    assert by_name["b"].expected_count == 2
    assert by_name["b"].detected_count == 0
    assert by_name["b"].deviation == 1.0
    assert by_name["c"].expected_count == 0
    assert by_name["c"].detected_count == 1
    assert by_name["c"].deviation == 1.0

    summary = summarize_rows(rows)
    assert summary.expected_total == 6
    assert summary.detected_total == 4
    assert summary.mean_deviation == 0.625
    assert summary.max_deviation == 1.0
    assert summary.diff_count == 3
