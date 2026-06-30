#!/usr/bin/env bash
# Build API + worker PyInstaller bundles + Next.js standalone frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/desktop/build_api.sh"
bash "$ROOT/desktop/build_worker.sh"
bash "$ROOT/desktop/build_frontend.sh"
echo ""
echo "All desktop bundles ready:"
echo "  desktop/dist/open-notebook-api/"
echo "  desktop/dist/open-notebook-worker/"
echo "  desktop/resources/frontend/"
