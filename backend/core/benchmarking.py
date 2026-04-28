from __future__ import annotations

from dataclasses import dataclass

from core.models import ResultItem


@dataclass(frozen=True)
class BenchmarkRow:
    symbol_name: str
    expected_count: int
    detected_count: int
    deviation: float


@dataclass(frozen=True)
class BenchmarkSummary:
    expected_total: int
    detected_total: int
    mean_deviation: float
    max_deviation: float
    diff_count: int


def count_results(results: list[ResultItem]) -> dict[str, int]:
    return {item.name: item.count for item in results}


def compare_counts(expected: dict[str, int], actual: dict[str, int]) -> list[BenchmarkRow]:
    rows: list[BenchmarkRow] = []
    for symbol_name in sorted(set(expected) | set(actual)):
        expected_count = expected.get(symbol_name, 0)
        detected_count = actual.get(symbol_name, 0)
        deviation = (
            abs(detected_count - expected_count) / expected_count if expected_count else float(bool(detected_count))
        )
        rows.append(BenchmarkRow(symbol_name, expected_count, detected_count, deviation))
    return rows


def summarize_rows(rows: list[BenchmarkRow]) -> BenchmarkSummary:
    expected_rows = [row for row in rows if row.expected_count > 0]
    return BenchmarkSummary(
        expected_total=sum(row.expected_count for row in rows),
        detected_total=sum(row.detected_count for row in rows),
        mean_deviation=sum(row.deviation for row in expected_rows) / max(1, len(expected_rows)),
        max_deviation=max((row.deviation for row in expected_rows), default=0.0),
        diff_count=sum(1 for row in rows if row.expected_count != row.detected_count),
    )
