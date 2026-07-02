#!/usr/bin/env bash
# Pre-download Docling layout/OCR models for offline PyInstaller worker bundles.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${DOCLING_MODELS_DIR:-$ROOT/desktop/cache/docling-models}"

echo "==> Docling models -> $OUT"
uv run --project "$ROOT" python "$ROOT/desktop/download_docling_models.py" "$OUT"
