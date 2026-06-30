#!/usr/bin/env python3
"""
PyInstaller entry point for the Open Notebook surreal-commands worker.

Usage (dev):
    uv run python desktop/entry_worker.py

Usage (frozen):
    ./open-notebook-worker/open-notebook-worker

Equivalent to:
    surreal-commands-worker --import-modules commands
"""

from __future__ import annotations

import os
import sys

from desktop.runtime_bootstrap import bootstrap

bootstrap()

from dotenv import load_dotenv

load_dotenv()

from commands import register_commands
from surreal_commands.cli.worker import main


def _default_argv() -> None:
    """Match supervisord / Makefile: import commands from the app package."""
    if len(sys.argv) == 1:
        sys.argv.extend(["--import-modules", "commands"])

    # Optional env override (comma-separated module names)
    env_modules = os.environ.get("SURREAL_COMMANDS_MODULES", "").strip()
    if env_modules and "--import-modules" not in sys.argv:
        sys.argv.extend(["--import-modules", env_modules])


def run() -> None:
    _default_argv()
    register_commands()
    frozen = getattr(sys, "frozen", False)
    print(f"Starting Open Notebook worker (frozen={frozen})")
    main()


if __name__ == "__main__":
    run()
