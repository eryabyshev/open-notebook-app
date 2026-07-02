#!/usr/bin/env bash
# Build Open Notebook worker with PyInstaller (--onedir).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Sync Python dependencies"
uv sync --group desktop

echo "==> Pre-download tiktoken encoding"
uv run python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

echo "==> Pre-download Docling models (layout, OCR, …)"
bash "$ROOT/desktop/download_docling_models.sh"

echo "==> Build worker bundle (PyInstaller --onedir)"
uv run pyinstaller --clean --noconfirm \
  --distpath "$ROOT/desktop/dist" \
  --workpath "$ROOT/desktop/build" \
  "$ROOT/desktop/open-notebook-worker.spec"

echo ""
echo "Build complete:"
echo "  $ROOT/desktop/dist/open-notebook-worker/open-notebook-worker"
echo ""
echo "Run (requires SurrealDB + API for job submission):"
echo "  uv run --env-file .env desktop/dist/open-notebook-worker/open-notebook-worker"
