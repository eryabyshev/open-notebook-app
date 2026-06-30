"""
Path helpers for normal development and PyInstaller frozen (desktop) builds.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Repository root in dev; directory containing the executable when frozen."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def bundle_root() -> Path:
    """Root of bundled read-only resources (_MEIPASS in PyInstaller onedir)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", project_root()))
    return project_root()


def resource_path(relative: str) -> Path:
    """Resolve a project-relative path in dev and inside a frozen bundle."""
    return bundle_root() / relative


def migration_path(filename: str) -> str:
    """Absolute path to a SurrealDB migration file."""
    return str(resource_path(f"open_notebook/database/migrations/{filename}"))
