#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Backend compile =="
(
  cd "$ROOT_DIR/backend"
  .venv/bin/python -m compileall main.py core
)

echo
echo "== Backend lint =="
(
  cd "$ROOT_DIR/backend"
  .venv/bin/ruff check .
  .venv/bin/black --check .
  .venv/bin/mypy \
    main.py \
    benchmark.py \
    fallback_benchmark.py \
    core/benchmarking.py \
    core/colors.py \
    core/config.py \
    core/detector.py \
    core/legend_extractor.py \
    core/models.py \
    core/pdf_render.py \
    core/storage.py \
    tests
)

echo
echo "== Backend tests =="
(
  cd "$ROOT_DIR/backend"
  .venv/bin/pytest
)

echo
echo "== Reference benchmark =="
(
  cd "$ROOT_DIR/backend"
  .venv/bin/python benchmark.py
)

if [[ "${ELEKTROSCAN_FALLBACK_BENCHMARK:-0}" == "1" ]]; then
  echo
  echo "== Fallback benchmark =="
  (
    cd "$ROOT_DIR/backend"
    .venv/bin/python fallback_benchmark.py --strict
  )
fi

echo
echo "== Frontend build =="
(
  cd "$ROOT_DIR/frontend"
  npm run lint
  npm run build
  npm run test:e2e
)

if [[ "${ELEKTROSCAN_API_SMOKE:-0}" == "1" ]]; then
  echo
  echo "== API smoke =="
  "$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/scripts/api_smoke.py"
fi

echo
echo "Verification complete."
