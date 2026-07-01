#!/usr/bin/env bash
# Print disk usage of desktop packaging artifacts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

print_size() {
  local label="$1"
  local path="$2"
  if [[ -e "$path" ]]; then
    du -sh "$path" | awk -v label="$label" '{printf "  %-22s %s\n", label, $1}'
  else
    printf "  %-22s (missing)\n" "$label"
  fi
}

echo "Desktop bundle sizes:"
print_size "SurrealDB" "$ROOT/desktop/resources/surrealdb"
print_size "API (PyInstaller)" "$ROOT/desktop/dist/open-notebook-api"
print_size "Worker (PyInstaller)" "$ROOT/desktop/dist/open-notebook-worker"
print_size "Frontend standalone" "$ROOT/desktop/resources/frontend"
print_size "Electron pack" "$ROOT/desktop/resources/electron-dist"

if compgen -G "$ROOT/desktop/resources/electron-dist/mac-arm64/*.app" > /dev/null 2>&1; then
  print_size "macOS .app total" "$ROOT/desktop/resources/electron-dist/mac-arm64/Open Notebook.app"
fi

echo ""
echo "Tip: full .dmg/.exe installers are larger; expect ~600 MB – 1 GB with docling/torch worker."
