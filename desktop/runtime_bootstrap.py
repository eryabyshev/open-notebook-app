"""Shared bootstrap for desktop PyInstaller entry points."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def bootstrap() -> Path:
    """
    Configure cwd and sys.path for dev and frozen runs.

    Returns the application root directory.
    """
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
        os.chdir(root)
    else:
        root = Path(__file__).resolve().parent.parent
        os.chdir(root)
        root_str = str(root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

    return root
