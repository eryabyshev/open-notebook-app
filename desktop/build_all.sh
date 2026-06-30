#!/usr/bin/env bash
# Build API + worker PyInstaller bundles.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/desktop/build_api.sh"
bash "$ROOT/desktop/build_worker.sh"
echo ""
echo "All desktop Python bundles ready under desktop/dist/"
