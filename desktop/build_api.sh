#!/usr/bin/env bash
# Build Open Notebook API with PyInstaller (--onedir).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Sync Python dependencies"
uv sync --group desktop

echo "==> Pre-download tiktoken encoding (offline tokenization)"
uv run python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

echo "==> Build API bundle (PyInstaller --onedir)"
uv run pyinstaller --clean --noconfirm --distpath "$ROOT/desktop/dist" --workpath "$ROOT/desktop/build" "$ROOT/desktop/open-notebook-api.spec"

echo ""
echo "Build complete:"
echo "  $ROOT/desktop/dist/open-notebook-api/open-notebook-api"
echo ""
echo "Run (requires SurrealDB on SURREAL_URL):"
echo "  cd $ROOT && uv run --env-file .env desktop/dist/open-notebook-api/open-notebook-api"
