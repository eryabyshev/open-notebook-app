#!/usr/bin/env bash
# Build desktop installer (PyInstaller bundles + SurrealDB + electron-builder --dir).
#
# Prerequisites: uv sync --group desktop, frontend npm install, electron npm install
#
# Usage:
#   bash desktop/build_installer.sh
#   bash desktop/build_installer.sh darwin-arm64   # fetch SurrealDB for target OS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PLATFORM="${1:-}"

echo "==> App icon"
uv run python desktop/generate_app_icon.py

echo "==> SurrealDB binary"
if [[ -n "$PLATFORM" ]]; then
  bash "$ROOT/desktop/download_surrealdb.sh" "$PLATFORM"
else
  bash "$ROOT/desktop/download_surrealdb.sh"
fi

echo "==> PyInstaller API + worker + frontend standalone"
bash "$ROOT/desktop/build_all.sh"

echo "==> Electron pack (--dir)"
cd "$ROOT/desktop/electron"
npm run pack

echo ""
echo "==> Artifact sizes"
bash "$ROOT/desktop/estimate_installer_size.sh"

echo ""
echo "Packaged app directory:"
echo "  $ROOT/desktop/resources/electron-dist/"
