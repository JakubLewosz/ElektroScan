import json
import shutil
from pathlib import Path

from core.benchmarking import compare_counts, count_results, summarize_rows
from core.detector import analyze_session
from core.storage import create_session_dir


def main() -> None:
    backend_dir = Path(__file__).resolve().parent
    expected = json.loads((backend_dir / "samples" / "expected_counts.json").read_text(encoding="utf-8"))
    context = json.loads((backend_dir / "samples" / "reference_context.json").read_text(encoding="utf-8"))

    session_id, session_dir = create_session_dir()
    source_pdf = session_dir / "source.pdf"
    shutil.copyfile(backend_dir / "samples" / "plan.pdf", source_pdf)

    progress = []
    result = analyze_session(
        session_id,
        source_pdf,
        excluded_zones=[],
        hidden_layers=context.get("hiddenLayersUsed", []),
        on_progress=lambda event: progress.append(event.model_dump()),
    )
    actual = count_results(result.results)
    rows = compare_counts(expected, actual)
    summary = summarize_rows(rows)

    print(f"session: {session_id}")
    print(f"progress events: {len(progress)}")
    print(f"expected total: {summary.expected_total}")
    print(f"detected total: {summary.detected_total}")
    print(f"boxes: {len(result.boxes)}")
    print(f"mean deviation: {summary.mean_deviation:.4f}")
    print(f"max deviation: {summary.max_deviation:.4f}")

    for row in rows:
        if row.expected_count != row.detected_count:
            print(f"DIFF {row.expected_count:>3} {row.detected_count:>3} {row.deviation:.2%} {row.symbol_name}")


if __name__ == "__main__":
    main()
