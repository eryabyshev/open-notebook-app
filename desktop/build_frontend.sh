#!/usr/bin/env bash
# Build Next.js standalone frontend for desktop/Electron (port 8502).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
OUT="$ROOT/desktop/resources/frontend"

echo "==> Build Next.js standalone"
cd "$FRONTEND"
if [[ ! -d node_modules ]]; then
  echo "Installing frontend dependencies..."
  npm install
fi
npm run build

echo "==> Copy standalone bundle to desktop/resources/frontend"
rm -rf "$OUT"
mkdir -p "$OUT"

# Use standalone/. (not standalone/*) — glob * skips hidden dirs like .next (BUILD_ID).
cp -a "$FRONTEND/.next/standalone/." "$OUT/"
mkdir -p "$OUT/.next/static"
cp -a "$FRONTEND/.next/static/." "$OUT/.next/static/"
if [[ -d "$FRONTEND/public" ]]; then
  mkdir -p "$OUT/public"
  cp -a "$FRONTEND/public/." "$OUT/public/"
fi

if [[ ! -f "$OUT/.next/BUILD_ID" ]]; then
  echo "ERROR: standalone bundle incomplete — missing $OUT/.next/BUILD_ID" >&2
  exit 1
fi

echo ""
echo "Frontend bundle ready:"
echo "  $OUT/server.js"
echo ""
echo "Run with Electron standalone mode:"
echo "  cd desktop/electron && OPEN_NOTEBOOK_FRONTEND_MODE=standalone npm run dev"
