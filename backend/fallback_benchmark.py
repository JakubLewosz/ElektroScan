from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from core.benchmarking import compare_counts, count_results, summarize_rows
from core.detector import analyze_session
from core.legend_extractor import extract_legend_templates
from core.storage import create_session_dir


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fallback detector benchmark without the reference profile.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when fallback counts differ from the accepted fallback baseline.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Optional path for a machine-readable benchmark report.",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent
    expected = _load_json(backend_dir / "samples" / "fallback_expected_counts.json")
    context = _load_json(backend_dir / "samples" / "reference_context.json")
    hidden_layers = list(context.get("hiddenLayersUsed", []))

    session_id, session_dir = create_session_dir()
    source_pdf = session_dir / "source.pdf"
    shutil.copyfile(backend_dir / "samples" / "plan.pdf", source_pdf)

    progress = []
    templates = extract_legend_templates(session_id, source_pdf, hidden_layers=hidden_layers)
    result = analyze_session(
        session_id,
        source_pdf,
        excluded_zones=[],
        hidden_layers=hidden_layers,
        on_progress=lambda event: progress.append(event.model_dump()),
        use_reference_profile=False,
    )

    actual = count_results(result.results)
    rows = compare_counts(expected, actual)
    summary = summarize_rows(rows)
    report = {
        "session": session_id,
        "templates": len(templates),
        "progressEvents": len(progress),
        "expectedTotal": summary.expected_total,
        "detectedTotal": summary.detected_total,
        "boxes": len(result.boxes),
        "meanDeviation": summary.mean_deviation,
        "maxDeviation": summary.max_deviation,
        "diffCount": summary.diff_count,
        "rows": [
            {
                "symbolName": row.symbol_name,
                "expected": row.expected_count,
                "detected": row.detected_count,
                "deviation": row.deviation,
            }
            for row in rows
        ],
    }

    print(f"session: {session_id}")
    print(f"templates: {len(templates)}")
    print(f"progress events: {len(progress)}")
    print(f"expected total: {summary.expected_total}")
    print(f"detected total: {summary.detected_total}")
    print(f"boxes: {len(result.boxes)}")
    print(f"mean deviation: {summary.mean_deviation:.4f}")
    print(f"max deviation: {summary.max_deviation:.4f}")
    print(f"diff count: {summary.diff_count}")
    print()
    print("expected detected deviation symbol")
    for row in rows:
        print(f"{row.expected_count:>8} {row.detected_count:>8} {row.deviation:>8.2%} {row.symbol_name}")

    if args.report_json:
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.strict and summary.diff_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
