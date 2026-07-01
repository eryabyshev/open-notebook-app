#!/usr/bin/env bash
# Install/sync Python deps required for desktop dev (API + worker).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_VERSION="$(cat .python-version 2>/dev/null || echo 3.12)"
SITE_PACKAGES="$ROOT/.venv/lib/python${PYTHON_VERSION}/site-packages"

repair_broken_typer() {
  # uv can leave dist-info/metadata while package files are missing; import then fails
  # but "uv sync" / "uv pip install" only report "Checked" and skip reinstall.
  local dist_info
  shopt -s nullglob
  dist_info=("$SITE_PACKAGES"/typer-*.dist-info)
  shopt -u nullglob

  if ((${#dist_info[@]} > 0)) && [[ ! -f "$SITE_PACKAGES/typer/__init__.py" ]]; then
    echo "==> Removing corrupted typer install (metadata present, package files missing)"
    rm -rf "$SITE_PACKAGES"/typer-*.dist-info "$SITE_PACKAGES/typer"
  fi
}

verify_worker_deps() {
  # Use venv python directly; `uv run` syncs to the lockfile and can undo `uv pip install`.
  "$ROOT/.venv/bin/python" -c "
from importlib.metadata import version
import typer
import rich
import shellingham
import surreal_commands
print('typer', version('typer'))
print('rich', version('rich'))
print('surreal_commands', version('surreal-commands'))
"
}

echo "==> uv lock"
uv lock

echo "==> uv sync"
uv sync

repair_broken_typer

echo "==> install worker CLI deps"
uv sync --reinstall-package typer --reinstall-package rich --reinstall-package shellingham

echo "==> verify worker deps"
if ! verify_worker_deps; then
  echo "==> verification failed; force-reinstall worker CLI deps"
  rm -rf "$SITE_PACKAGES"/typer-*.dist-info "$SITE_PACKAGES/typer" 2>/dev/null || true
  uv sync --reinstall-package typer --reinstall-package rich --reinstall-package shellingham
  verify_worker_deps
fi

echo "==> done"
